import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

test('every banking interface button declares its intended form behavior', () => {
  const source = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  const file = ts.createSourceFile('App.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const buttonElements = [];

  function visit(node) {
    if (ts.isJsxOpeningElement(node) && node.tagName.getText(file) === 'button') {
      buttonElements.push(node);
    }
    ts.forEachChild(node, visit);
  }

  visit(file);
  assert.ok(buttonElements.length > 0, 'expected banking controls to include buttons');
  for (const button of buttonElements) {
    const typeAttribute = button.attributes.properties.find(
      (attribute) => ts.isJsxAttribute(attribute) && attribute.name.getText(file) === 'type'
    );
    assert.ok(typeAttribute, `button at line ${file.getLineAndCharacterOfPosition(button.pos).line + 1} has no explicit type`);
    assert.ok(
      ['button', 'submit'].includes(typeAttribute.initializer?.text),
      `button at line ${file.getLineAndCharacterOfPosition(button.pos).line + 1} must use button or submit type`
    );
  }
});
