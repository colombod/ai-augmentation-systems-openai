'use strict';
// OpenAI Decisions wire adapter. The caller supplies filtered declared state only.
module.exports = (post) => ({
  async ask({ id, question, state, cfg, key, timeoutMs }) {
    const q = {name: id, instructions: question.instructions,
      ...(question.type === 'choice'
        ? {type: 'choice', choices: Object.entries(question.criteria).map(([value, description]) => ({value, description}))}
        : {type: 'predicate'})};
    const r = await post(cfg.endpoint, JSON.stringify({model: cfg.model, input: JSON.stringify(state), questions: [q]}), {Authorization: `Bearer ${key}`}, timeoutMs);
    if (r.failure) return {error: true, reason: r.failure};
    if (r.status !== 200) return {error: true, reason: `http_${r.status}`, status: r.status};
    let json;
    try { json = JSON.parse(r.text); } catch (_) { return {error: true, reason: 'bad_response'}; }
    if (!json || !Array.isArray(json.answers) || json.answers.length !== 1) return {error: true, reason: 'bad_response'};
    const a = json.answers[0];
    if (!a || a.name !== id) return {error: true, reason: 'bad_response'};
    if (a.type === 'refusal') return {error: true, reason: 'refusal'};
    const unit = (x) => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
    const extra = {model: typeof json.model === 'string' ? json.model : null, usage: json.usage || {}};
    if (question.type === 'noul' && a.type === 'predicate' && unit(a.probability))
      return {answer: a.probability >= .5 ? 'yes' : 'no', p: a.probability, ...extra};
    const options = Object.keys(question.criteria || {});
    if (question.type !== 'choice' || a.type !== 'choice' || !options.includes(a.choice) || !unit(a.confidence) || !Array.isArray(a.probabilities))
      return {error: true, reason: 'bad_response'};
    const probabilities = {};
    for (const row of a.probabilities) {
      if (!row || !options.includes(row.value) || !unit(row.probability) || Object.hasOwn(probabilities, row.value)) return {error: true, reason: 'bad_response'};
      probabilities[row.value] = row.probability;
    }
    if (Object.keys(probabilities).length !== options.length || Math.abs(Object.values(probabilities).reduce((x,y)=>x+y,0)-1) > .01)
      return {error: true, reason: 'bad_response'};
    return {answer: a.choice, confidence: a.confidence, probabilities, ...extra};
  },
});
