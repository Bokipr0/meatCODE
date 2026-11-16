"""Compare direct retrieval with real MCP stdio calls; never grade answers implicitly."""
import argparse,asyncio,json,os,statistics,sys,time
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from server.mcp_pilot.backend import Backend

QUERIES=['Maillard reaction cysteine ribose','lipid oxidation aroma','plant protein beany flavour','GC-MS aroma compounds','zzzxqvnomatchzzzxqv']

def signature(value,graph=False):
    return [r['item_id'] if graph else r['id'] for r in value.get('items' if graph else 'results',[])]

def metrics(values):
    ordered=sorted(values)
    return {'n':len(values),'median_ms':round(statistics.median(values),2),'p95_ms':round(ordered[max(0,__import__('math').ceil(.95*len(ordered))-1)],2)}

async def run(args):
    root=Path(__file__).resolve().parents[2]
    backend=Backend(args.corpus_env,args.graph_env)
    params=StdioServerParameters(command=sys.executable,args=['-m','server.mcp_pilot.main','--corpus-env',args.corpus_env,'--graph-env',args.graph_env],cwd=str(root))
    records=[];start=time.perf_counter()
    async with stdio_client(params) as (reader,writer):
      async with ClientSession(reader,writer) as client:
        init=await client.initialize();startup=round((time.perf_counter()-start)*1000,2)
        tools=(await client.list_tools()).tools
        assert {t.name for t in tools}=={'search','fetch','search_knowledge_graph'}
        assert all(t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in tools)
        for tool,method in [('search',backend.search),('search_knowledge_graph',backend.graph_search)]:
          for repeat in range(args.repeats):
            for question in QUERIES:
              start=time.perf_counter();direct=method(question);direct_ms=(time.perf_counter()-start)*1000
              start=time.perf_counter();result=await client.call_tool(tool,{'query':question});mcp_ms=(time.perf_counter()-start)*1000
              assert not result.isError, f'{tool} failed'
              remote=result.structuredContent
              if remote is None:remote=json.loads(result.content[0].text)
              same=signature(direct,tool!='search')==signature(remote,tool!='search')
              assert same,'MCP changed evidence ordering'
              records.append({'tool':tool,'query':question,'repeat':repeat,'direct_ms':round(direct_ms,2),'mcp_ms':round(mcp_ms,2),'matches':len(signature(remote,tool!='search')),'identical_evidence':same,'mode':remote.get('mode')})
        sources=backend.search('Maillard')
        assert sources['results'],'Cannot test source fetch without a result'
        source_id=str(sources['results'][0]['id'])
        fetched=await client.call_tool('fetch',{'id':source_id});assert not fetched.isError
        malformed=await client.call_tool('fetch',{'id':'1; DROP TABLE sources'});assert malformed.isError
        excessive=await client.call_tool('search_knowledge_graph',{'query':'Maillard','limit':999});assert excessive.isError
        empty=await client.call_tool('search',{'query':' '});assert empty.isError
        forbidden=await client.call_tool('run_sql',{'sql':'SELECT * FROM user_research.chat_turns'});assert forbidden.isError
    summary={'date':'2026-11-16','transport':'MCP stdio, official Python SDK 1.30.0','protocol':init.protocolVersion,
      'initialize_ms':startup,'checks':{'tool_discovery':True,'annotations_read_only':True,'fetch_source':True,'invalid_input_rejected':True,'arbitrary_sql_unavailable':True,'all_evidence_identical':True},
      'scope':'Transport/retrieval smoke benchmark. Not an answer-quality comparison, ChatGPT test, vector benchmark or human scientific validation.',
      'conditions':'Direct calls precede MCP calls; database cache/network effects may favor MCP. No model calls or research-log writes.',
      'retrievals':{},'runs':records}
    for tool in ['search','search_knowledge_graph']:
      subset=[r for r in records if r['tool']==tool]
      summary['retrievals'][tool]={'direct':metrics([r['direct_ms'] for r in subset]),'mcp':metrics([r['mcp_ms'] for r in subset]),'nonempty':sum(r['matches']>0 for r in subset),'total':len(subset)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus-env',required=True);p.add_argument('--graph-env',required=True);p.add_argument('--repeats',type=int,default=3);p.add_argument('--output',type=Path,required=True);asyncio.run(run(p.parse_args()))
