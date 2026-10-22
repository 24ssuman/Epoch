import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../src/moonlight.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {lunarRelativeFlux,lunarGlow,lunarTransmission}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('phase brightness follows the published magnitude law rather than illuminated area',()=>{
 assert.equal(lunarRelativeFlux(-12.73,1),1);
 const quarter=lunarRelativeFlux(undefined,.5);
 assert.ok(Math.abs(quarter-10**(-.4*(.026*90+4e-9*90**4)))<1e-12);
 assert.ok(quarter>.09&&quarter<.092);
 assert.ok(lunarRelativeFlux(undefined,.1)<quarter);
 assert.equal(lunarRelativeFlux(-12.73,0),0);
});
test('magnitude includes distance: twice as far has one quarter the flux',()=>{
 assert.ok(Math.abs(lunarRelativeFlux(-12.73+5*Math.log10(2),1)-.25)<1e-12);
 assert.ok(lunarGlow(undefined,1)>lunarGlow(undefined,.5));
 assert.ok(lunarGlow(undefined,.5)>lunarGlow(undefined,.1));
 assert.equal(lunarGlow(-12.73,1,4,1),0);
 assert.ok(lunarGlow(-12.73,1,8)>lunarGlow(-12.73,1,0));
});
test('atmospheric attenuation and horizon gating remain separate from phase',()=>{
 assert.equal(lunarTransmission(-10,true),0);assert.equal(lunarTransmission(0,false),0);
 assert.equal(lunarTransmission(45,false),1);
 assert.ok(lunarTransmission(5,true)<lunarTransmission(60,true));
 assert.ok(lunarTransmission(60,true)<1);
 assert.equal(lunarRelativeFlux(undefined,NaN),0);
});
