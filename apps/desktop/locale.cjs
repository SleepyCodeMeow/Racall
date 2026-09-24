const fs = require('node:fs');
const path = require('node:path');
const catalogs = { en: require('../shared/locales/en.json'), ru: require('../shared/locales/ru.json') };
const validLocale = value => value === 'en' || value === 'ru';
function readLocale(file) {
  try {
    const value = JSON.parse(fs.readFileSync(file, 'utf8')).locale;
    return validLocale(value) ? value : null;
  } catch { return null; }
}
function initializeLocale(dataDir, resourcesDir) {
  fs.mkdirSync(dataDir, { recursive: true });
  const preference = path.join(dataDir, 'preferences.json');
  const installed = readLocale(path.join(resourcesDir, 'installer-language.json')) || 'en';
  // Exclusive creation prevents startup from overwriting a concurrent saved choice.
  try { fs.writeFileSync(preference, JSON.stringify({ locale: installed }) + '\n', { flag: 'wx' }); }
  catch (error) { if (error.code !== 'EEXIST') throw error; }
  return readLocale(preference) || 'en';
}
function nativeMessage(dataDir, key, params = {}) {
  const locale = readLocale(path.join(dataDir, 'preferences.json')) || 'en';
  return (catalogs[locale][key] || catalogs.en[key] || key).replace(/\{(\w+)\}/g, (match, name) => String(params[name] ?? match));
}
module.exports = { initializeLocale, readLocale, nativeMessage };
