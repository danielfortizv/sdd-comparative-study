import React, { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen } from '../../frontend/node_modules/@testing-library/react/dist/index.js';
import { afterEach, beforeEach, expect, test, vi } from '../../frontend/node_modules/vitest/dist/index.js';
import App from '../../frontend/src/App';

function deferred<T=any>() { let resolve!:(v:T)=>void; let reject!:(e:any)=>void; const promise=new Promise<T>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}; }
function state(id='old', extra:any={}) {return {id,board:Array.from({length:20},()=>Array(10).fill(null)),active_piece:{type:'O',origin:[0,3],cells:[[0,3],[0,4],[1,3],[1,4]]},status:'playing',score:0,total_lines:0,level:1,gravity_interval_ms:500,next_piece:'T',hold_piece:null,can_hold:true,...extra};}
const response=(s:any)=>({ok:true,json:()=>Promise.resolve(s)});
let calls:any[]=[];
let creates:any[]=[];
let mutations:any[]=[];
async function flush(){await act(async()=>{for(let n=0;n<12;n++)await Promise.resolve();});}
beforeEach(()=>{
 vi.useFakeTimers(); calls=[];creates=[];mutations=[];
 vi.stubGlobal('fetch',vi.fn((url:any,init:any)=>{
  calls.push({url:String(url),method:init?.method});
  const pending=deferred();
  if(String(url)==='/api/games')creates.push(pending);else mutations.push({url:String(url),...pending});
  return pending.promise;
 }));
 vi.spyOn(console,'error').mockImplementation(()=>{});
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();vi.restoreAllMocks();});
async function start(){render(<App/>);await flush();creates[0].resolve(response(state()));await flush();}
async function restart(){fireEvent.click(screen.getByRole('button',{name:'Start New Game'}));await flush();creates.at(-1).resolve(response(state('new')));await flush();}
const hold=()=>fireEvent.click(screen.getByRole('button',{name:'Hold Piece'}));
const move=()=>fireEvent.keyDown(window,{key:'ArrowLeft'});
const tickCount=()=>calls.filter(x=>x.url.endsWith('/tick')).length;

test('S2-18 obsolete StrictMode create rejection cannot show an error even with null rejection',async()=>{
 render(<StrictMode><App/></StrictMode>);await flush();creates[1].resolve(response(state('strict')));await flush();await restart();
 creates[0].reject(null);await flush();
 expect(screen.queryByText(/Could not connect to the Tetris API/)).toBeNull();
 expect(screen.getByText('new')).toBeTruthy();
});
