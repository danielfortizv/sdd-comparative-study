// Independent researcher tests. All fixtures use BMAD's native JSON and explicit Start UX.
import React,{StrictMode} from 'react';
import {render,screen,fireEvent,act,cleanup} from '@testing-library/react';
import {describe,it,expect,vi,beforeEach,afterEach} from 'vitest';
import App from '../../frontend/src/App';

const state=(id='old-session',score=101,extra={})=>({id,status:'playing',board:Array.from({length:20},()=>Array(10).fill(0)),active_piece:{shape:'O',origin:{row:5,col:4},cells:[{row:5,col:4},{row:5,col:5},{row:6,col:4},{row:6,col:5}]},score,total_lines:10,level:2,gravity_interval_ms:450,next_piece:'J',hold_piece:null,can_hold:true,...extra});
const response=(value)=>({ok:true,status:200,json:()=>Promise.resolve(value)});
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return {promise,resolve,reject};};
let fetchMock;
const flush=async()=>{await act(async()=>{for(let n=0;n<12;n++)await Promise.resolve();});};
const advance=async(ms)=>{await act(async()=>{vi.advanceTimersByTime(ms);});await flush();};
const key=async(value)=>{fireEvent.keyDown(window,{key:value});await flush();};
const start=async()=>{fireEvent.click(screen.getByRole('button',{name:'Start Session',exact:true}));await flush();};
const restart=async()=>{fireEvent.click(screen.getByRole('button',{name:'Restart Session',exact:true}));await flush();};
const mount=()=>render(<StrictMode><App/></StrictMode>);
const score=(value)=>expect(screen.getByText(String(value),{exact:true})).toBeTruthy();

beforeEach(()=>{vi.useFakeTimers();fetchMock=vi.fn();vi.stubGlobal('fetch',fetchMock);});
afterEach(()=>{cleanup();vi.clearAllTimers();vi.useRealTimers();vi.unstubAllGlobals();});

describe('Independent BMAD lifecycle and contract acceptance',()=>{
  it('explicit Start, authoritative HUD and C/button Hold, terminal timer stop',async()=>{
    fetchMock.mockResolvedValueOnce(response(state())).mockResolvedValueOnce(response(state('old-session',202,{hold_piece:'O',next_piece:'S',can_hold:false}))).mockResolvedValueOnce(response(state('old-session',303,{status:'game_over',active_piece:null,can_hold:false})));
    const view=mount();expect(fetchMock).toHaveBeenCalledTimes(0);await start();score(101);
    expect(view.container.textContent).toContain('450ms');
    expect(view.container.querySelectorAll('.board .cell')).toHaveLength(200);
    await key('C');score(202);expect(String(fetchMock.mock.calls[1][0])).toContain('/hold');
    expect(screen.getByRole('button',{name:/Hold Piece \(C\)/i}).disabled).toBe(true);
    await advance(450);score(303);expect(view.container.querySelectorAll('.cell-active')).toHaveLength(0);
    const count=fetchMock.mock.calls.length;await advance(5000);expect(fetchMock).toHaveBeenCalledTimes(count);
  });

  it('serializes two queued manual mutations and waits a full450ms after LAST response',async()=>{
    const a=deferred(),b=deferred();
    fetchMock.mockResolvedValueOnce(response(state())).mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise).mockResolvedValue(response(state('old-session',404)));
    mount();await start();await key('ArrowLeft');await key('ArrowRight');
    expect(fetchMock).toHaveBeenCalledTimes(2);await advance(2000);expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(async()=>a.resolve(response(state('old-session',202))));await flush();expect(fetchMock).toHaveBeenCalledTimes(3);score(202);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).direction).toBe('right');
    await advance(2000);expect(fetchMock).toHaveBeenCalledTimes(3);
    await act(async()=>b.resolve(response(state('old-session',303))));await flush();score(303);
    await advance(449);expect(fetchMock).toHaveBeenCalledTimes(3);await advance(1);expect(fetchMock).toHaveBeenCalledTimes(4);expect(String(fetchMock.mock.calls[3][0])).toContain('/tick');
  });

  for(const phase of ['fetch','json'])for(const outcome of ['resolve','reject-null','reject-undefined']){
    it(`restart preempts oldHold ${phase}/${outcome}; late oldfinally cannot steal newqueue ownership`,async()=>{
      const old=deferred(),fresh=deferred();
      fetchMock.mockResolvedValueOnce(response(state())).mockReturnValueOnce(phase==='fetch'?old.promise:Promise.resolve({ok:true,json:()=>old.promise})).mockResolvedValueOnce(response(state('new-session',202))).mockReturnValueOnce(fresh.promise).mockResolvedValue(response(state('new-session',404)));
      mount();await start();fireEvent.click(screen.getByRole('button',{name:/Hold Piece \(C\)/i}));await flush();
      expect(fetchMock).toHaveBeenCalledTimes(2);await restart();score(202);expect(fetchMock).toHaveBeenCalledTimes(3);
      await key('c');expect(fetchMock).toHaveBeenCalledTimes(4);expect(String(fetchMock.mock.calls[3][0])).toContain('/new-session/hold');
      await act(async()=>{if(outcome==='resolve')old.resolve(phase==='fetch'?response(state('old-session',999)):state('old-session',999));else old.reject(outcome==='reject-null'?null:undefined);});await flush();score(202);expect(screen.queryByText('999',{exact:true})).toBeNull();
      await advance(1000);expect(fetchMock).toHaveBeenCalledTimes(4);
      await act(async()=>fresh.resolve(response(state('new-session',303,{can_hold:false,hold_piece:'O'}))));await flush();score(303);
      await advance(449);expect(fetchMock).toHaveBeenCalledTimes(4);await advance(1);expect(fetchMock).toHaveBeenCalledTimes(5);expect(String(fetchMock.mock.calls[4][0])).toContain('/new-session/tick');
    });
  }

  for(const phase of ['fetch','json'])it(`newest start owns state despite late olderstart ${phase}`,async()=>{
    const old=deferred();
    fetchMock.mockReturnValueOnce(phase==='fetch'?old.promise:Promise.resolve({ok:true,json:()=>old.promise})).mockResolvedValueOnce(response(state('new-session',202))).mockResolvedValue(response(state('new-session',303)));
    mount();await start();await start();score(202);
    await act(async()=>old.resolve(phase==='fetch'?response(state('old-session',999)):state('old-session',999)));await flush();score(202);
    await advance(450);expect(String(fetchMock.mock.calls.at(-1)[0])).toContain('/new-session/tick');
  });

  it('unmount discards pending JSON and cannot restore gravity',async()=>{
    const old=deferred();fetchMock.mockResolvedValueOnce(response(state())).mockResolvedValueOnce({ok:true,json:()=>old.promise});
    const view=mount();await start();await key('ArrowDown');view.unmount();
    await act(async()=>old.resolve(state('old-session',999)));await flush();await advance(2000);expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
