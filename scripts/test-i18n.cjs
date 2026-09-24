const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const en = require('../apps/shared/locales/en.json');
const ru = require('../apps/shared/locales/ru.json');
const { initializeLocale, nativeMessage } = require('../apps/desktop/locale.cjs');
const root = path.resolve(__dirname, '..');
assert.deepEqual(Object.keys(en).sort(), Object.keys(ru).sort());
for (const key of Object.keys(en)) {
  assert.ok(en[key].trim() && ru[key].trim(), key);
  assert.deepEqual((en[key].match(/\{\w+\}/g) || []).sort(), (ru[key].match(/\{\w+\}/g) || []).sort(), key);
}
const file = path.join(root, 'apps/web/lib/translations.ts');
const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText;
const loaded = new Module(file, module); loaded.filename = file; loaded.paths = Module._nodeModulePaths(path.dirname(file)); loaded._compile(compiled, file);
const { translate, pluralize, localizeMessage } = loaded.exports;
assert.equal(translate('settings.title'), 'Settings');
assert.equal(pluralize('source.ready', 1, 'en'), '1 source ready');
assert.equal(pluralize('source.ready', 2, 'en'), '2 sources ready');
for (const [count, ending] of [[0, 'источников готовы'], [1, 'источник готов'], [2, 'источника готовы'], [5, 'источников готовы'], [11, 'источников готовы'], [21, 'источник готов'], [22, 'источника готовы']]) {
  assert.equal(pluralize('source.ready', count, 'ru'), `${count} ${ending}`);
}
assert.equal(localizeMessage('Провайдер вернул HTTP 401. Проверьте URL, ключ и имя модели.', 'en'), 'The provider returned HTTP 401. Check the URL, key, and model name.');
assert.equal(localizeMessage('The file exceeds 25 MB', 'ru'), 'Размер файла превышает 25 МБ');
assert.equal(localizeMessage('Unrecognized provider diagnostic', 'ru'), 'Unrecognized provider diagnostic');
const run = path.join(root, 'test-results', 'locale-unit-' + Date.now());
const resources = path.join(run, 'resources'); fs.mkdirSync(resources, { recursive: true });
assert.equal(initializeLocale(path.join(run, 'default'), resources), 'en');
fs.writeFileSync(path.join(resources, 'installer-language.json'), JSON.stringify({ locale: 'ru' }));
const profile = path.join(run, 'selected');
assert.equal(initializeLocale(profile, resources), 'ru');
assert.equal(nativeMessage(profile, 'native.startTitle'), 'Не удалось запустить Racall');
fs.writeFileSync(path.join(profile, 'preferences.json'), JSON.stringify({ locale: 'en' }));
assert.equal(initializeLocale(profile, resources), 'en', 'Installer language must not overwrite an existing preference');
fs.writeFileSync(path.join(resources, 'installer-language.json'), JSON.stringify({ locale: 'unknown' }));
assert.equal(initializeLocale(path.join(run, 'unsupported'), resources), 'en');
console.log(JSON.stringify({ passed: true, catalogKeys: Object.keys(en).length, checks: ['catalog parity', 'placeholder parity', 'plural rules', 'service messages', 'English default', 'installer seed', 'upgrade preference preservation', 'unsupported locale fallback'] }));
