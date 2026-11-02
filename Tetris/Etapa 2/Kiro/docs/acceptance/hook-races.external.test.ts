// Researcher acceptance checks. Imports real production hook/API; no app mocks.
import { afterAll, afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { writeFileSync } from 'node:fs';
import { useGame } from '../../frontend/src/useGame';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
function state(id: string, row = 0, col = 3) {
  return { id, status: 'playing', board: Array.from({length:20}, () => Array(10).fill(0)),
    active_piece: { type:'I', origin:[row,col], cells:[[row,col],[row,col+1],[row,col+2],[row,col+3]] },
    score:0,total_lines:0,level:1,gravity_interval_ms:500,next_piece:'O',hold_piece:null,can_hold:true };
}
type Request = { path:string, fetch:ReturnType<typeof deferred<Response>>, body:ReturnType<typeof deferred<any>>, jsonCalled:boolean, bodyResolved:boolean };
let requests: Request[] = [];
const observations: any[] = [];
async function flush() { await act(async () => { for(let i=0;i<12;i++) await Promise.resolve(); }); }
async function headers(request: Request) {
  request.fetch.resolve({ok:true, status:200, json:() => { request.jsonCalled=true; return request.body.promise; }} as Response);
  await flush();
}
async function body(request: Request, value:any) {
  request.bodyResolved=true; request.body.resolve(value); await flush();
}
async function complete(request: Request, value:any) { await headers(request); await body(request,value); }
async function advance(ms:number) { await act(async () => { vi.advanceTimersByTime(ms); }); await flush(); }
async function mounted() {
  const hook=renderHook(() => useGame());
  await flush(); expect(requests).toHaveLength(1);
  await complete(requests[0],state('A'));
  return hook;
}
function snapshot(label:string, hook:any) {
  const row={ label, visible_id:hook.result.current.state?.id,
    visible_row:hook.result.current.state?.active_piece?.origin[0],
    requests:requests.map(r=>({path:r.path,json_called:r.jsonCalled,body_resolved:r.bodyResolved})) };
  observations.push(row); return row;
}
beforeEach(() => {
  requests=[]; vi.useFakeTimers();
  vi.stubGlobal('fetch',vi.fn((url:any) => {
    const request={path:new URL(String(url),'http://localhost').pathname,fetch:deferred<Response>(),body:deferred<any>(),jsonCalled:false,bodyResolved:false};
    requests.push(request); return request.fetch.promise;
  }));
});
afterEach(() => { cleanup(); vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); });
afterAll(() => {
  writeFileSync(process.env.RACE_OBSERVATIONS_PATH!,JSON.stringify({researcher_created:true,coverage_enabled:false,observations},null,2)+'\n');
});

it('R1 restart pending: input must not relabel old A request as generation B',async()=>{
  const hook=await mounted();
  act(()=>{void hook.result.current.restart();}); await flush();
  expect(requests[1].path).toBe('/api/games'); // B creation genuinely pending
  act(()=>{void hook.result.current.hold();}); await flush();
  // Permit a correct implementation to defer/drop input while creation waits.
  const oldHold=requests.find(r=>r.path==='/api/games/A/hold');
  if(oldHold) { await headers(oldHold); expect(oldHold.jsonCalled).toBe(true); }
  await complete(requests[1],state('B'));
  expect(hook.result.current.state?.id).toBe('B');
  if(oldHold) await body(oldHold,{...state('A'),hold_piece:'I',can_hold:false,next_piece:'T',
    active_piece:{type:'O',origin:[0,3],cells:[[0,3],[0,4],[1,3],[1,4]]}});
  snapshot('R1 after B creation then delayed A Hold body',hook);
  expect(hook.result.current.state?.id).toBe('B');
});

it('R2 manual body pending: automatic tick must not cause visible reversal',async()=>{
  const hook=await mounted();
  act(()=>{void hook.result.current.move('down');}); await flush();
  const manual=requests.find(r=>r.path.endsWith('/move'))!;
  expect(manual).toBeDefined(); await headers(manual); expect(manual.jsonCalled).toBe(true);
  await advance(500);
  const tick=requests.find(r=>r.path.endsWith('/tick'));
  // If serialized/cancelled correctly no tick is in flight yet, so no reversal.
  if(tick) await complete(tick,state('A',2));
  const rowBefore=hook.result.current.state?.active_piece?.origin[0];
  await body(manual,state('A',1));
  const observed=snapshot('R2 tick response row2 then delayed manual body row1',hook);
  expect(observed.visible_row).toBeGreaterThanOrEqual(rowBefore!);
});

it('R3 manual completion must not release guard owned by unresolved automatic tick',async()=>{
  const hook=await mounted();
  act(()=>{void hook.result.current.move('left');}); await flush();
  const manual=requests.find(r=>r.path.endsWith('/move'))!;
  await headers(manual); expect(manual.jsonCalled).toBe(true);
  await advance(500);
  const firstTick=requests.find(r=>r.path.endsWith('/tick'));
  if(firstTick) { await headers(firstTick); expect(firstTick.jsonCalled).toBe(true); }
  await body(manual,state('A',0,2));
  const tickCountBefore=requests.filter(r=>r.path.endsWith('/tick')).length;
  await advance(500);
  const unresolvedTicks=requests.filter(r=>r.path.endsWith('/tick')&&!r.bodyResolved);
  const observed=snapshot('R3 manual complete, one more interval, first tick body still pending',hook);
  Object.assign(observed,{tick_count_before:tickCountBefore,unresolved_tick_count:unresolvedTicks.length});
  expect(unresolvedTicks.length).toBeLessThanOrEqual(1);
});
