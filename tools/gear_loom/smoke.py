from gearcore.core import read,ROOT,require,GateError
from gearcore.witnesses import topology,graph,motion
import copy,math
p=read(ROOT/'fixtures/plan.json');m=read(ROOT/'fixtures/mesh.json');topology(m);graph(p)
t={'requested_rpm':12,'samples':[{'t_ms':i*1000/60,'angles':[g['phase']+g['ratio'][0]/g['ratio'][1]*12*math.tau/60*i/60 for g in p['gears']]} for i in range(241)]};motion(t,p);caught=[]
def expect(code,fn):
 try:fn()
 except GateError as e:require(e.code==code,'WRONG_DIAGNOSTIC',str(e));caught.append(code);return
 raise GateError('SURVIVING_MUTANT',code)
bad=copy.deepcopy(m);bad['triangles'].pop();expect('EDGE_INCIDENCE',lambda:topology(bad))
bad=copy.deepcopy(m);bad['triangles'][0].reverse();expect('WINDING_CONFLICT',lambda:topology(bad))
bad=copy.deepcopy(p);bad['edges'].pop();expect('DISCONNECTED_TRAIN',lambda:graph(bad))
bad=copy.deepcopy(p);bad['gears'][3]['ratio']=[-1,6];expect('RATIO_DECLARATION',lambda:graph(bad))
bad=copy.deepcopy(t)
for row in bad['samples']:row['angles'][3]*=1.01
expect('ANGULAR_SPEED',lambda:motion(bad,p))
bad=copy.deepcopy(t)
for row in bad['samples']:row['angles'][1]+=math.pi/40
expect('MESH_PHASE',lambda:motion(bad,p))
bad=copy.deepcopy(t);bad['samples'][1]['t_ms']=0;expect('FRAME_CLOCK_ORDER',lambda:motion(bad,p))
bad=copy.deepcopy(t)
for row in bad['samples']:row['t_ms']*=200
expect('ANGULAR_ALIAS_RISK',lambda:motion(bad,p))
print('PASS: 3 positive contracts and',len(caught),'negative controls; optimized:',not __debug__)
