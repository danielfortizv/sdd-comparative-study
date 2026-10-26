"""Additional researcher edge case; preserve the original six-case harness unchanged."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent/'Tessl'/'docs'/'acceptance'
base=(root/'races.external.test.tsx').read_text()
head=base.split("test('S2-18 restart",1)[0]
case=r'''test('S2-18 obsolete StrictMode create rejection cannot show an error even with null rejection',async()=>{
 render(<StrictMode><App/></StrictMode>);await flush();creates[1].resolve(response(state('strict')));await flush();await restart();
 creates[0].reject(null);await flush();
 expect(screen.queryByText(/Could not connect to the Tetris API/)).toBeNull();
 expect(screen.getByText('new')).toBeTruthy();
});
'''
(root/'falsey.external.test.tsx').write_text(head+case,encoding='utf-8')
config=(root/'vitest.external.config.mjs').read_text().replace("include:['races.external.test.tsx']","include:['falsey.external.test.tsx']")
(root/'vitest.falsey.config.mjs').write_text(config,encoding='utf-8')
print('Prepared separate one-case researcher harness; original six-case files unchanged.')
