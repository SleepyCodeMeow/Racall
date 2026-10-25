/** Synthetic completion protocol for desktop workflow checks. Never runs a model. */
const assert = require('node:assert/strict');
const http = require('node:http');

function studioProvider() {
  const calls = [];
  const errors = [];
  const sockets = new Set();
  const heldQuestions = new Set();
  let cancelled = 0;
  const server = http.createServer(async (request, response) => {
    try {
      assert.equal(request.method, 'POST');
      assert.equal(request.url, '/v1/chat/completions');
      assert.equal(request.headers.authorization, 'Bearer ollama');
      let text = '';
      for await (const chunk of request) {
        text += chunk;
        assert.ok(text.length < 200000);
      }
      const payload = JSON.parse(text);
      assert.equal(payload.stream, true);
      const input = JSON.parse(payload.messages[1].content);
      calls.push(input);
      response.writeHead(200, { 'Content-Type': 'text/event-stream' });
      if (input.question?.includes('Hold generation') && !input.claims && !heldQuestions.has(input.question)) {
        heldQuestions.add(input.question);
        response.write(': waiting for synthetic cancellation\n\n');
        response.on('close', () => { cancelled++; });
        return;
      }
      let result;
      if (input.claims) {
        result = { supported_claim_ids: input.claims.map(claim => claim.claim_id) };
      } else if (!input.evidence) {
        result = { queries: ['Marigold launch October'] };
      } else {
        const passage = input.evidence.find(item => item.quote.includes('October 18'));
        assert.ok(passage, 'Selected fixture passage must reach the writer');
        const text = input.answer_language === 'ru'
          ? 'Запуск проекта Marigold назначен на 18 октября.'
          : 'Marigold launches on October 18.';
        const item = { text, evidence_ids: [passage.id] };
        result = input.format === 'summary' ? { items: [item] }
          : input.format === 'study_guide' ? { sections: [{ title: input.answer_language === 'ru' ? 'Запуск' : 'Launch', items: [item] }] }
          : input.format === 'review_questions' ? { questions: [{
            question: input.answer_language === 'ru' ? 'Когда запустится проект Marigold?' : 'When does Marigold launch?',
            answer: text, evidence_ids: [passage.id],
          }] } : { claims: [item], message: '' };
      }
      const send = (delta, finish_reason = null) => response.write(
        `data: ${JSON.stringify({ choices: [{ index: 0, delta, finish_reason }] })}\n\n`,
      );
      send({ content: JSON.stringify(result) });
      send({}, 'stop');
      response.end('data: [DONE]\n\n');
    } catch (error) {
      errors.push(error.message);
      if (!response.headersSent) response.writeHead(500);
      response.end();
    }
  });
  server.on('connection', socket => {
    sockets.add(socket);
    socket.on('close', () => sockets.delete(socket));
  });
  return {
    calls, errors,
    get cancelled() { return cancelled; },
    async start() {
      await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
      return `http://127.0.0.1:${server.address().port}/v1`;
    },
    async close() {
      for (const socket of sockets) socket.destroy();
      await new Promise(resolve => server.close(resolve));
    },
  };
}

module.exports = { studioProvider };
