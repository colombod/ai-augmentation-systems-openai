#!/usr/bin/env node
'use strict';
// Explicit operator-selected config. No Claude role markers or inherited provider.
const fs = require('node:fs');
const J = require('./lib/judge.js');
async function main(args) {
  if (args[0] === 'questions' && args.length === 1) return {code: 0, result: J.loadCatalogue()};
  const protectedWorkflow = args[args.length - 1] === '--protected';
  if (protectedWorkflow) args = args.slice(0, -1);
  if (!['ask', 'evaluate'].includes(args[0]) || (protectedWorkflow && args[0] !== 'evaluate') || args.length !== 6 || args[2] !== '--config' || args[4] !== '--state') throw Error('usage: judge.js questions | ask|evaluate <question> --config <file> --state <file|-> [--protected]');
  let team, state;
  try { team = JSON.parse(fs.readFileSync(args[3], 'utf8')); state = JSON.parse(fs.readFileSync(args[5] === '-' ? 0 : args[5], 'utf8')); }
  catch (_) { throw Error('config and state must be readable JSON'); }
  const result = await J[args[0]](args[1], state, {team, protected: protectedWorkflow, timeoutMs: 30000});
  return {code: result.skipped || result.error || (result.policy && !result.policy.gate_allowed) ? 3 : 0, result};
}
if (require.main === module) main(process.argv.slice(2)).then(({code, result}) => {console.log(JSON.stringify(result,null,2));process.exitCode=code;}, e => {console.error(e.message);process.exitCode=2;});
module.exports = {main};
