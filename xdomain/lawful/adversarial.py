"""Hand-built documents the metric must catch, each next to a clean control for the same request.
Three families: valid-but-unlawful (the XSD passes them), lawful-but-wrong-request, and escape hatches.
Each case names the part that must fall below 1 and must score below its control. Written by me; model-free."""
from specs import eval_specs

HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<X3D profile="{p}" version="4.0"><head>{h}</head><Scene>\n{s}\n</Scene></X3D>'
def doc(scene, profile="Interchange", head=""): return HEAD.format(p=profile, h=head, s=scene)

MAT = '<Appearance><Material diffuseColor="{c}"/></Appearance>'
BOX = '<Transform DEF="Base" translation="0 0 0"><Shape DEF="BaseShape">' + MAT.format(c="0.5 0.5 0.5") + '<Box DEF="BaseBox" size="2 1 2"/></Shape></Transform>'
def cyl(y=1.0, x=0.0, h=1.0): return f'<Transform DEF="Top" translation="{x} {y} 0"><Shape>' + MAT.format(c="1 1 0") + f'<Cylinder radius="0.4" height="{h:g}"/></Shape></Transform>'
ON_TOP = BOX + cyl()                         # box top at y=0.5, cylinder bottom at y=0.5

SPIN_OK = ('<Transform DEF="Spinner"><Shape>' + MAT.format(c="0 0.4 1") + '<Box/></Shape></Transform>'
           '<TimeSensor DEF="Clock" cycleInterval="4" loop="true"/>'
           '<OrientationInterpolator DEF="Spin" key="0 0.5 1" keyValue="0 1 0 0 0 1 0 3.14159 0 1 0 6.28318"/>'
           '<ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Spin" toField="set_fraction"/>'
           '<ROUTE fromNode="Spin" fromField="value_changed" toNode="Spinner" toField="set_rotation"/>')
def table(leg_y=-0.5):
    legs = "".join(f'<Transform translation="{x} {leg_y} {z}"><Shape USE="Leg"/></Transform>' for x, z in ((0.9, 0.4), (-0.9, 0.4), (-0.9, -0.4)))
    return ('<Transform translation="0 0.05 0"><Shape>' + MAT.format(c="0.6 0.4 0.2") + '<Box size="2 0.1 1"/></Shape></Transform>'
            f'<Transform translation="0.9 {leg_y} -0.4"><Shape DEF="Leg">' + MAT.format(c="0.6 0.4 0.2") + '<Cylinder radius="0.05" height="1"/></Shape></Transform>' + legs)
CONE_DOWN = '<Transform rotation="1 0 0 3.14159"><Shape>' + MAT.format(c="1 1 1") + '<Cone/></Shape></Transform>'
CONE_UP = '<Transform><Shape>' + MAT.format(c="1 1 1") + '<Cone/></Shape></Transform>'

def cases():
    S = eval_specs(); A3, C1, B1, A5 = S["X-A3"], S["X-C1"], S["X-B1"], S["X-A5"]
    ctl = {"X-A3": doc(ON_TOP), "X-C1": doc(SPIN_OK), "X-B1": doc(table()), "X-A5": doc(CONE_DOWN)}
    C = [
     # ---- valid-but-unlawful
     ("unlawful/wrong-type-USE", "X-A3", "lawful", doc(ON_TOP + '<Transform translation="3 0 0"><Transform USE="BaseShape"/></Transform>')),
     ("unlawful/geometry-USE-of-other-kind", "X-A3", "lawful", doc(ON_TOP + '<Transform translation="3 0 0"><Shape><Cylinder USE="BaseBox"/></Shape></Transform>')),
     ("unlawful/material-as-geometry", "X-A3", "lawful", doc(BOX.replace('<Material diffuseColor="0.5 0.5 0.5"/>', '<Material containerField="geometry" diffuseColor="0.5 0.5 0.5"/>') + cyl())),
     ("unlawful/box-in-appearance-field", "X-A3", "lawful", doc(ON_TOP + '<Shape><Box containerField="appearance"/><Box size="0.1 0.1 0.1"/></Shape>')),
     ("unlawful/texture-default-field-in-PhysicalMaterial", "X-A3", "lawful", doc(ON_TOP.replace('<Appearance><Material diffuseColor="1 1 0"/></Appearance>', '<Appearance><PhysicalMaterial baseColor="1 1 0"><ImageTexture url=\'"t.png"\'/></PhysicalMaterial></Appearance>'), "Immersive")),
     # ---- lawful but not what was asked
     ("wrong-request/sphere-not-cylinder", "X-A3", "use_type", doc(BOX + cyl().replace('<Cylinder radius="0.4" height="1"/>', '<Sphere radius="0.5"/>'))),
     ("wrong-request/cylinder-sinks-into-box", "X-A3", "spatial", doc(BOX + cyl(y=0.6))),
     ("wrong-request/cylinder-floats-above-box", "X-A3", "spatial", doc(BOX + cyl(y=1.6))),
     ("wrong-request/cylinder-beside-box", "X-A3", "spatial", doc(BOX + cyl(x=3.0))),
     ("wrong-request/interpolator-not-driven", "X-C1", "use_type", doc(SPIN_OK.replace('<ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Spin" toField="set_fraction"/>', ''))),
     ("wrong-request/table-legs-float", "X-B1", "spatial", doc(table(leg_y=-1.5))),
     ("wrong-request/cone-points-up", "X-A5", "spatial", doc(CONE_UP)),
     # ---- escape hatches
     ("hatch/profile-Full", "X-A3", "hatches", doc(ON_TOP, "Full")),
     ("hatch/no-profile-needed-component", "X-A3", "hatches", doc(ON_TOP, "Interchange", '<component name="NURBS" level="1"/>')),
     ("hatch/unrequested-Script", "X-A3", "hatches", doc(ON_TOP + '<Script DEF="S"><![CDATA[ecmascript: function initialize() {}]]></Script>', "Immersive")),
     ("hatch/looser-profile", "X-A3", "hatches", doc(ON_TOP, "Immersive")),
    ]
    return S, ctl, C
