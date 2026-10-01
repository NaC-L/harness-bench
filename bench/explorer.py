"""Compile a result directory into an offline, dependency-free session explorer."""
from __future__ import annotations

import json
from pathlib import Path

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
    saved_report = root / 'REPORT.md'
    return {'title': results.name, 'runs': runs,
            'report': saved_report.read_text(encoding='utf-8')
            if _inside(root, saved_report) and saved_report.is_file() else None}


def render(data: dict) -> str:
    # JSON script data must not be able to close its containing element.
    payload = json.dumps(data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return TEMPLATE.replace('__BENCH_DATA__', payload)


def compile_explorer(results: Path, out: Path) -> None:
    if out.exists():
        raise ValueError(f'output file already exists: {out}')
    data = collect(results)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(render(data))


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Benchmark run explorer</title>
<style>
:root{color-scheme:dark;--bg:#10151d;--panel:#19212d;--line:#3c4a60;--text:#edf2fa;--muted:#b4c2d6;--accent:#7ed6ed}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}header,main{max-width:1500px;margin:auto;padding:24px}h1{margin:0;font-size:28px}h2{font-size:21px}h3{font-size:17px}p{margin:8px 0}.muted,small{color:var(--muted)}button,input,select{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:8px 12px}button{cursor:pointer}button:hover{border-color:var(--accent)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}a{color:var(--accent)}.filters,.stats,.tabs{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}.stat{background:var(--panel);padding:12px 18px;border-radius:8px}.stat strong{display:block;font-size:23px}.layout{display:grid;grid-template-columns:minmax(320px,440px) minmax(0,1fr);gap:24px}.run-list{max-height:75vh;overflow:auto;display:flex;flex-direction:column;gap:8px}.run{text-align:left;width:100%;padding:12px}.run.selected{background:#243d50;border:2px solid var(--accent)}.run strong{display:block}.run small{display:block}.pass{color:#9de0b6}.fail{color:#ffb3b3}.unknown{color:var(--muted)}.card,details{border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:12px 16px;background:var(--panel)}summary{cursor:pointer;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,Consolas,monospace;margin:12px 0}dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:5px 18px}dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}.tabs button[aria-pressed=true]{border:2px solid var(--accent);background:#243d50}.badge{font-size:12px;border:1px solid var(--line);padding:2px 7px;border-radius:4px;margin-right:8px}#detail{min-width:0}#timeline-controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center}input[type=search]{min-width:180px;flex:1}#report{max-height:60vh;overflow:auto}[hidden]{display:none!important}@media(max-width:800px){header,main{padding:16px}.layout{grid-template-columns:1fr}.run-list{max-height:36vh}h1{font-size:24px}dl{grid-template-columns:1fr}dt{margin-top:8px}}
</style></head><body>
<header><h1>Benchmark run explorer</h1><p id="subtitle" class="muted"></p><p class="muted">Offline snapshot · No external scripts or network requests · Missing measurements stay unknown</p><div id="stats" class="stats"></div><details id="report-wrap" hidden><summary>Published comparison report (saved snapshot, not re-scored)</summary><pre id="report"></pre></details></header>
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
$('subtitle').textContent=data.title;
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
