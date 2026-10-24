import asyncio, os, sys, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
REPO=os.path.expanduser("~/Projects/x3d/x3d_mcp")
async def main(names):
    async with stdio_client(StdioServerParameters(command=REPO+"/.venv/bin/python", args=["-m","src.server"], cwd=REPO)) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            for n in names:
                res=await s.call_tool("describe_node",{"node_type":n}); t="".join(getattr(c,"text","") for c in res.content)
                try:
                    d=json.loads(t); print("=====",n,d.get("containerField"),d.get("baseType"))
                    for f in d["fields"]:
                        if f["name"] in ("bboxCenter","bboxDisplay","bboxSize","metadata","IS","DEF","USE","class","id","style"): continue
                        print("  ",f["name"],f["type"],f["accessType"],"def=",f.get("default"),"->",f.get("acceptableNodeTypes","")[:80], (f.get("simpleType") or ""))
                except Exception as e: print(n, t[:300])
asyncio.run(main(sys.argv[1:]))
