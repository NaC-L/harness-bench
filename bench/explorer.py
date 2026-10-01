"""Compile a result directory into an offline, dependency-free session explorer."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from . import report


ARTIFACTS = ('patch.diff', 'check.txt', 'check-visible.txt', 'stderr.txt')


def _inside(root: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(root)


def collect(results: Path) -> dict:
    """Only embed artifacts inside the supplied result directory, never external paths."""
    root = results.resolve()
    runs = []
    for row in report.load(root / 'runs.jsonl'):
        artifact = Path(row.get('artifact_dir') or row.get('run_id', ''))
        candidates = [root / artifact, artifact, root / str(row.get('run_id', ''))]
        directory = next((p.resolve() for p in candidates
                          if _inside(root, p) and p.is_dir() and p.resolve() != root), None)
        files = {}
        if directory:
            for name in ARTIFACTS:
                path = directory / name
                if _inside(root, path) and path.is_file():
                    files[name] = path.read_text(encoding='utf-8', errors='replace')
            sessions = sorted(directory.glob('session*.jsonl'))
            if (directory / 'sessions').is_dir():
                sessions += sorted((directory / 'sessions').rglob('*.jsonl'))
            if not sessions and (directory / 'stdout.jsonl').is_file():
                sessions = [directory / 'stdout.jsonl']
            for path in sessions:
                if _inside(root, path) and path.is_file():
                    files[path.relative_to(directory).as_posix()] = path.read_text(
                        encoding='utf-8', errors='replace')
        runs.append({'row': row, 'files': files})
    charts = []
    for path in sorted((root / 'charts').glob('*.svg'),
                       key=lambda p: (p.name != 'summary.svg', p.name)):
        if not _inside(root, path) or not path.is_file():
            continue
        raw = path.read_bytes()
        try:
            svg = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(f'invalid saved chart: {path}') from exc
        if svg.tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError(f'not an SVG chart: {path}')
        charts.append({
            'name': f'charts/{path.name}',
            'title': svg.findtext('{http://www.w3.org/2000/svg}title') or path.stem,
            'description': svg.findtext('{http://www.w3.org/2000/svg}desc') or '',
            # SVGs are images, never inline markup: embedded scripts cannot execute.
            'image': 'data:image/svg+xml;base64,' + base64.b64encode(raw).decode('ascii'),
        })
    saved_report = root / 'REPORT.md'
    return {'title': results.name, 'runs': runs, 'charts': charts,
            'report': saved_report.read_text(encoding='utf-8')
            if _inside(root, saved_report) and saved_report.is_file() else None}


def render(data: dict) -> str:
    # JSON script data must not be able to close its containing element.
    payload = json.dumps(data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return TEMPLATE.replace('__BENCH_STYLE__', STYLE).replace('__BENCH_DATA__', payload)


def compile_explorer(results: Path, out: Path) -> None:
    if out.exists():
        raise ValueError(f'output file already exists: {out}')
    data = collect(results)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(render(data))


STYLE = r'''
:root{color-scheme:dark;--bg:#000;--panel:#0a0a0a;--line:rgba(255,255,255,.14);--text:#ededed;--muted:#a1a1a1;--tertiary:#757575;--accent:#44cfff;--mono:'Geist Mono','JetBrains Mono',ui-monospace,Consolas,monospace;--sans:Geist,Inter,system-ui,-apple-system,'Segoe UI',sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.7 var(--sans)}
a{color:var(--accent);text-underline-offset:4px}
a:hover{color:var(--text)}
:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
h1,h2,h3{font-weight:600;line-height:1.2}
h1{font-size:52px;letter-spacing:-.045em;margin:12px 0 24px}
h2{font-size:28px;letter-spacing:-.035em;margin:0 0 16px}
h3{font-size:18px;letter-spacing:-.02em;margin:0 0 12px}
p{margin:8px 0 16px}
.muted,small{color:var(--muted)}
.micro,.eyebrow,small,button,select,.source,.stat,dt,dd,.badge,figcaption,summary,th,td{font-family:var(--mono);font-variant-numeric:tabular-nums}
.micro,.eyebrow,figcaption,th{font-size:11px;letter-spacing:.06em}
.micro,.eyebrow,th{text-transform:uppercase}
.eyebrow{color:var(--accent)}
.topbar{height:56px;border-bottom:1px solid var(--line)}
.topbar-inner{max-width:1200px;margin:auto;height:100%;padding:0 32px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{color:var(--text);font-weight:600;letter-spacing:-.02em;text-decoration:none}
.brand:before{content:'';display:inline-block;width:12px;height:12px;margin-right:12px;background:var(--accent);box-shadow:4px 4px 0 #0c3848}
.topbar a:not(.brand){font:11px var(--mono);letter-spacing:.06em;text-transform:uppercase;text-decoration:none;border-bottom:1px dotted var(--accent);padding-bottom:3px}
.page-header,main{max-width:1200px;margin:auto;padding:0 32px}
.page-header{padding-top:80px}
.lede{max-width:760px;font-size:18px;line-height:1.6;color:var(--muted)}
.stats{display:flex;flex-wrap:wrap;border-block:1px solid var(--line);margin:32px 0}
.stat{flex:1;min-width:170px;padding:24px;border-right:1px solid var(--line)}
.stat:last-child{border-right:0}
.stat small{display:block;text-transform:uppercase;letter-spacing:.06em;font-size:11px;overflow-wrap:anywhere}
.stat strong{display:block;font-size:28px;font-weight:400;line-height:1.3;margin-top:8px}
main{padding-top:48px;padding-bottom:96px}
button,input,select{font-size:12px;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:10px 12px;min-height:40px;max-width:100%}
input{font-family:var(--sans)}
button{cursor:pointer}
button:hover{border-color:var(--accent);background:#0a0a0a}
button[aria-pressed=true]{border-color:var(--accent);color:var(--accent);background:#041d26}
.filters,.tabs{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.filters input[type=search]{min-width:180px;flex:1}
.section-heading{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px}
.section-heading h2{margin:0}
.layout{display:grid;grid-template-columns:minmax(240px,320px) minmax(0,1fr);gap:32px;margin-top:24px}
.run-list{max-height:75vh;overflow:auto;display:flex;flex-direction:column}
.run{text-align:left;width:100%;padding:16px;border:0;border-bottom:1px solid var(--line);border-radius:0;border-left:2px solid transparent}
.run strong{display:block;font:600 15px/1.5 var(--sans);overflow-wrap:anywhere}
.run span,.run small{display:block;font-size:11px;margin-top:4px;overflow-wrap:anywhere}
.run.selected{border-left-color:var(--accent);background:#041d26}
.run:hover:not(.selected),.experiment:hover{background-color:#0a0a0a;background-image:repeating-conic-gradient(from 45deg,rgba(68,207,255,.035) 0% 25%,transparent 0% 50%);background-size:4px 4px}
.pass{color:#4ade80}.fail{color:#f4644a}.unknown{color:var(--muted)}
.card,details{border:1px solid var(--line);border-radius:0;margin:16px 0;padding:16px 20px;background:var(--bg)}
.card h3{font:12px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--accent)}
summary{font-size:12px;cursor:pointer;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.7 var(--mono);margin:16px 0}
.card pre{border-top:4px solid transparent;border-image:repeating-linear-gradient(90deg,#0c3848 0 2px,#44cfff 2px 3px,#000 3px 4px) 4;padding-top:12px}
dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:8px 24px;border-block:1px solid var(--line);padding:20px 0;font-size:12px}
dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}
.badge{font-size:11px;border:1px solid var(--line);padding:2px 7px;border-radius:2px;margin-right:8px}
#subtitle{overflow-wrap:anywhere}
#detail{min-width:0}
#detail h2{font-size:24px;overflow-wrap:anywhere}
#timeline-controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
#timeline-controls input[type=search]{flex:1;min-width:180px}
#timeline-controls label{font-size:12px}
input[type=checkbox]{min-height:0;accent-color:var(--accent)}
#report{max-height:60vh;overflow:auto}
.graphs{max-width:760px;margin:48px 0 0}
.graph-figure{margin:0}
.chart-viewport{overflow-x:auto;overscroll-behavior-x:contain}
.chart-viewport img{display:block;width:760px;max-width:none}
figcaption{color:var(--muted);margin-top:12px;line-height:1.6}
.graph-data{font:12px/1.7 var(--mono);overflow-wrap:anywhere}
.experiments{margin:48px 0;border-top:1px solid var(--line)}
.experiment{display:grid;grid-template-columns:48px minmax(0,1fr) 120px;gap:24px;padding:28px 0;border-bottom:1px solid var(--line);align-items:start}
.experiment h2{font-size:20px;line-height:1.4;margin:0 0 8px;overflow-wrap:anywhere}
.experiment h2 a{color:var(--text);text-decoration:none}
.experiment h2 a:hover{color:var(--accent)}
.experiment p{font:12px/1.7 var(--mono);color:var(--muted);margin:0 0 12px;overflow-wrap:anywhere}
.experiment .source{font-size:11px}
.experiment-mark{display:block;width:40px;height:40px;background-color:#041d26;background-image:repeating-conic-gradient(#44cfff 0% 25%,transparent 0% 50%);background-size:4px 4px;border:1px solid #0c3848}
.experiment-kind{font:10px/1.7 var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:right}
footer{margin-top:64px;padding-top:24px;border-top:1px solid var(--line);font:11px/1.8 var(--mono);color:var(--muted)}
[hidden]{display:none!important}
@media(max-width:800px){.layout{grid-template-columns:1fr}.run-list{max-height:36vh}}
@media(max-width:640px){.topbar-inner,.page-header,main{padding-left:16px;padding-right:16px}.page-header{padding-top:48px}h1{font-size:36px}h2{font-size:24px}.lede{font-size:16px}.stats{display:block}.stat{min-width:0;border-right:0;border-bottom:1px solid var(--line);padding:16px 0}.stat:last-child{border-bottom:0}.stat strong{font-size:24px}.experiment{grid-template-columns:32px minmax(0,1fr);gap:16px;padding:24px 0}.experiment-mark{width:28px;height:28px}.experiment-kind{grid-column:2;text-align:left}.experiment h2{font-size:18px}dl{grid-template-columns:1fr;gap:4px}dt{margin-top:8px}.card,details{padding:16px}.filters>*{width:100%}.graphs{margin-top:32px}main{padding-top:32px}#timeline-controls>*{width:100%}}
'''

TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Benchmark run explorer</title>
<style>
__BENCH_STYLE__
</style></head><body>
<div class="topbar"><nav class="topbar-inner" aria-label="Site"><a class="brand" href="https://github.com/NaC-L/harness-bench">Harness Bench</a><a id="index-link" hidden>Experiments</a></nav></div>
<header class="page-header"><p class="eyebrow">Research / Session explorer</p><h1>Inside the run.</h1><p id="subtitle" class="lede"></p><p class="micro muted">Offline snapshot · Missing measurements stay unknown</p><div id="stats" class="stats"></div><section class="graphs" aria-label="Published graphs"><div class="section-heading"><h2>Comparison graphs</h2><span class="micro muted">Saved evidence</span></div><div id="graph-tabs" class="tabs" aria-label="Choose graph"></div><div id="graph"></div></section><details id="report-wrap" hidden><summary>Published comparison report (saved snapshot, not re-scored)</summary><pre id="report"></pre></details></header>
<main><div class="filters"><input id="search" type="search" aria-label="Search task, harness or run ID" placeholder="Search task, harness or run ID"><select id="arm" aria-label="Harness"><option value="">All harnesses</option></select><select id="task" aria-label="Task"><option value="">All tasks</option></select><select id="status" aria-label="Result"><option value="">All results</option><option value="pass">Passed</option><option value="fail">Failed</option><option value="unknown">Unknown</option></select></div><p id="count" class="muted" aria-live="polite"></p><div class="layout"><nav aria-label="Benchmark runs" id="runs" class="run-list"></nav><section id="detail" aria-label="Selected run"><p>Select a run to inspect its session.</p></section></div></main>
<script type="application/json" id="bench-data">__BENCH_DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('bench-data').textContent);
const $=id=>document.getElementById(id);
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
const fmt=(v,d=0)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString(undefined,{maximumFractionDigits:d}):'unknown';
const result=r=>r.passed===true?'pass':r.passed===false?'fail':'unknown';
const pretty=v=>typeof v==='string'?v:JSON.stringify(v,null,2);
function block(parent,title,text,open=false){const n=el('details');n.open=open;n.append(el('summary',title),el('pre',text));parent.append(n);return n}
function pairs(parent,values){const dl=el('dl');for(const [k,v] of values){dl.append(el('dt',k),el('dd',v===null||v===undefined?'unknown':String(v)))}parent.append(dl)}
function graphs(){
  const charts=data.charts||[];
  if(!charts.length){
    $('graph').append(el('p','No saved comparison charts in this bundle. Inspect its recorded run measurements below.','muted'));
    return;
  }
  for(const chart of charts){
    const button=el('button',chart.name==='charts/summary.svg'?'Overview':chart.title);
    button.title=chart.title;
    button.setAttribute('aria-pressed','false');
    button.onclick=()=>{
      for(const b of $('graph-tabs').children)b.setAttribute('aria-pressed',b===button?'true':'false');
      const figure=el('figure',undefined,'graph-figure');
      const viewport=el('div',undefined,'chart-viewport'),image=el('img');
      viewport.tabIndex=0;
      viewport.setAttribute('role','region');
      viewport.setAttribute('aria-label',chart.title+'; scroll horizontally on narrow screens');
      image.src=chart.image;
      image.alt=chart.title+'. Saved chart; text values below.';
      viewport.append(image);
      figure.append(viewport,el('figcaption',`Snapshot: ${chart.name}. Original scope and captions preserved; run filters below do not change this plot. On narrow screens, scroll the plot sideways.`));
      if(chart.description){
        const text=el('details');
        text.append(el('summary','View plotted values and methodology'),el('p',chart.description,'graph-data'));
        figure.append(text);
      }
      $('graph').replaceChildren(figure);
    };
    $('graph-tabs').append(button);
  }
  $('graph-tabs').firstChild.click();
}
graphs();
if(data.index_href&&/^(?:\.\.\/)+index\.html$/.test(data.index_href)){$('index-link').href=data.index_href;$('index-link').hidden=false}
$('subtitle').textContent=data.title;
document.title=data.title+' · Harness Bench';
for(const key of ['harness','task'])for(const value of [...new Set(data.runs.map(x=>x.row[key]))].sort()){const o=el('option',value);o.value=value;$(key==='harness'?'arm':'task').append(o)}
for(const arm of [...new Set(data.runs.map(x=>x.row.harness))].sort()){const rs=data.runs.filter(x=>x.row.harness===arm);const n=el('div',undefined,'stat');n.append(el('small',arm),el('strong',`${rs.filter(x=>x.row.passed===true).length}/${rs.length} passed`));$('stats').append(n)}
if(data.report!==null){$('report-wrap').hidden=false;$('report').textContent=data.report}
let selected=null;
function filtered(){return data.runs.map((run,i)=>({run,i})).filter(({run:{row:r}})=>(!$('arm').value||r.harness===$('arm').value)&&(!$('task').value||r.task===$('task').value)&&(!$('status').value||result(r)===$('status').value)&&[r.task,r.harness,r.run_id].join(' ').toLowerCase().includes($('search').value.toLowerCase())).sort((a,b)=>String(a.run.row.task).localeCompare(String(b.run.row.task))||String(a.run.row.harness).localeCompare(String(b.run.row.harness))||a.run.row.trial-b.run.row.trial)}
function list(){const rs=filtered();$('runs').replaceChildren();$('count').textContent=`${rs.length} of ${data.runs.length} runs`;for(const {run:{row:r},i} of rs){const b=el('button',undefined,'run'+(i===selected?' selected':''));b.dataset.index=i;b.setAttribute('aria-pressed',i===selected?'true':'false');b.append(el('strong',r.task),el('span',`${result(r).toUpperCase()} · ${r.harness} · trial ${r.trial}`,result(r)),el('small',`${fmt(r.wall_time_sec,1)} s · ${fmt(r.metrics?.tool_calls)} tool calls`));b.onclick=()=>{location.hash='run='+i};$('runs').append(b)}if(!rs.length)$('runs').append(el('p','No matching runs. Clear the filters.','muted'))}
function timeline(parent,files){const names=Object.keys(files).filter(n=>n.endsWith('.jsonl'));if(!names.length){parent.append(el('p','Session unavailable: no transcript was captured or included in this bundle.','muted'));return}const controls=el('div');controls.id='timeline-controls';const choice=el('select');choice.setAttribute('aria-label','Session file');for(const name of names){const o=el('option',name);o.value=name;choice.append(o)}const search=el('input');search.type='search';search.placeholder='Search session content';search.setAttribute('aria-label','Search session content');const label=el('label');const thinking=el('input');thinking.type='checkbox';label.append(thinking,document.createTextNode(' Show captured reasoning'));const body=el('div');controls.append(choice,search,label);parent.append(controls,body);
function draw(){body.replaceChildren();let records=files[choice.value].split(/\r?\n/).filter(s=>s.trim()).map((s,i)=>{try{return {record:JSON.parse(s),line:i+1}}catch{return {record:{type:'malformed record',raw:s},line:i+1}}});const stream=choice.value==='stdout.jsonl';if(stream)records=records.filter(({record:r})=>!['message_start','message_update','tool_execution_update'].includes(r.type));let shown=0;for(const {record:r,line} of records){if(search.value&&!pretty(r).toLowerCase().includes(search.value.toLowerCase()))continue;const m=r.message;if(m&&['message','message_end'].includes(r.type)){const card=el('article',undefined,'card');card.append(el('h3',`${m.role||'message'}${m.toolName?' · '+m.toolName:''}`),el('small',r.timestamp?String(r.timestamp):m.timestamp?new Date(m.timestamp).toISOString():`Record ${line}`));const content=typeof m.content==='string'?[{type:'text',text:m.content}]:Array.isArray(m.content)?m.content:[];for(const b of content){if(b.type==='thinking'){if(thinking.checked)block(card,'Captured reasoning',b.thinking||b.text||'')}else if(b.type==='toolCall'||b.type==='tool_use'){block(card,`Tool call: ${b.name}`,pretty(b.arguments??b.input??{}),true)}else if(b.type==='text'){card.append(el('pre',b.text||''))}else{block(card,b.type||'Content block',pretty(b))}}if(m.usage)card.append(el('small',`Tokens: input ${fmt(m.usage.input)} · output ${fmt(m.usage.output)} · cache read ${fmt(m.usage.cacheRead)} · cache write ${fmt(m.usage.cacheWrite)}`));block(card,'Raw message record',pretty(r));body.append(card)}else{block(body,`${r.type||'record'}${r.customType?' · '+r.customType:''} · record ${line}`,pretty(r))}shown++}body.prepend(el('p',`${shown} records shown in file order`,'muted'));if(!shown)body.append(el('p','No matching session records.','muted'))}
choice.onchange=draw;search.oninput=draw;thinking.onchange=draw;draw()}
function show(i){if(!data.runs[i])return;selected=i;list();const {row:r,files}=data.runs[i],m=r.metrics||{};const d=$('detail');d.replaceChildren(el('h2',`${r.task} / ${r.harness} / trial ${r.trial}`));const s=el('p',`${result(r).toUpperCase()} · agent ${r.agent_completion||'unknown'}`,result(r));d.append(s);pairs(d,[['Wall time',`${fmt(r.wall_time_sec,2)} s`],['Model time',`${fmt(m.model_time_sec,2)} s`],['Models',(m.models||[]).join(', ')||'unknown'],['Tokens (input / output)',`${fmt(m.input_tokens)} / ${fmt(m.output_tokens)}`],['Cache (read / write)',`${fmt(m.cache_read_tokens)} / ${fmt(m.cache_write_tokens)}`],['Recorded cost (USD)',fmt(m.cost_usd,6)],['Requests / tool calls',`${fmt(m.requests)} / ${fmt(m.tool_calls)}`],['Visible tests (pass / fail)',`${fmt(r.visible_tests_pass)} / ${fmt(r.visible_tests_fail)}`],['Hidden tests (pass / fail)',`${fmt(r.hidden_tests_pass)} / ${fmt(r.hidden_tests_fail)}`],['Reproduced before edit',m.reproduced_before_first_edit],['Verified after final edit',m.verified_after_final_edit],['Run ID',r.run_id]]);const problems=[...(r.errors||[]),...(m.errors||[])];if(r.timed_out)problems.push('Agent timed out');if(r.check_timed_out)problems.push('Check timed out');if(r.tampered_files?.length)problems.push('Tampered files: '+r.tampered_files.join(', '));if(r.regressions?.length)problems.push('Regressions: '+pretty(r.regressions));if(problems.length)block(d,'Errors and safety signals',problems.join('\n'),true);if(m.final_message)block(d,'Final response',m.final_message,true);
const tabs=el('div',undefined,'tabs'),panel=el('div');d.append(tabs,panel);for(const name of ['Session','Checks','Patch','Metadata']){const b=el('button',name);b.setAttribute('aria-pressed','false');b.onclick=()=>{for(const button of tabs.children)button.setAttribute('aria-pressed',button===b?'true':'false');panel.replaceChildren();if(name==='Session')timeline(panel,files);else if(name==='Metadata')block(panel,'Complete run record',pretty(r),true);else{const wanted=name==='Patch'?['patch.diff']:['check.txt','check-visible.txt','stderr.txt'];for(const file of wanted)block(panel,file,files[file]===undefined?'Artifact unavailable.':files[file]||'(empty file)',true)}};tabs.append(b)}tabs.firstChild.click()}
for(const id of ['search','arm','task','status'])$(id).addEventListener(id==='search'?'input':'change',list);
function route(){const match=/^#run=(\d+)$/.exec(location.hash);if(match&&data.runs[Number(match[1])])show(Number(match[1]));else{selected=null;list();$('detail').replaceChildren(el('p','Select a run to inspect its session.'))}}
window.addEventListener('hashchange',route);route();
</script></body></html>'''
