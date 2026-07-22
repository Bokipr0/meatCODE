/**
 * MeatCODE — User Values & Paper-Rating Survey (v1)
 * Last updated: 2026-07-21 · Advisory · one-click Google Form generator
 *
 * HOW TO USE (2 minutes):
 *   1. Go to  https://script.google.com  → New project.
 *   2. Delete the sample code, paste ALL of this file.
 *   3. Click Run ▶ (select function: createMeatCODEForm). Authorize when asked (your own account).
 *   4. Open the Execution log — it prints the "EDIT" and "SHARE (live)" URLs.
 *      The live URL is what you send people; the edit URL is where you tweak wording.
 *   No API keys, no setup — Apps Script talks to your Google account directly.
 */

function createMeatCODEForm() {
  var form = FormApp.create('MeatCODE — User Values & Paper-Rating Survey')
    .setDescription(
      'Help shape MeatCODE — 5 minutes, before you’ve ever used it.\n\n' +
      'MeatCODE (a Good Food Institute · GFI Israel initiative) is building an AI research assistant ' +
      'that answers only from real, cited scientific sources. Before we show it to you, we want your ' +
      'honest expectations and frustrations with AI research tools today. There are no right answers — ' +
      'and at the end we’ll ask you to skim one real paper and rate it. Responses are anonymous.')
    .setProgressBar(true)
    .setCollectEmail(false);

  // ---- Part A ----
  form.addMultipleChoiceItem()
    .setTitle('Which best describes you?')
    .setChoiceValues(['Academic researcher / PI','Grad student or postdoc',
      'Flavor / food chemist (industry)','Alt-meat / food-product R&D','Data / AI / software'])
    .showOtherOption(true).setRequired(true);

  var q2 = form.addCheckboxItem()
    .setTitle('When you use general AI chatbots (ChatGPT, Claude, Gemini…) for scientific or technical questions, what frustrates you most?')
    .setHelpText('Select up to 3.')
    .setChoiceValues([
      'It makes things up / hallucinates facts',
      'I can’t verify where the answer came from (no real sources)',
      'It cites papers that don’t exist, or gets them wrong',
      'Not deep enough in my specific field',
      'Its knowledge feels outdated',
      'Answers are generic / surface-level',
      'It won’t admit when it doesn’t know',
      'It blends solid science with weak / blog-level claims'])
    .setRequired(true);
  q2.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(3).build());

  var q3 = form.addCheckboxItem()
    .setTitle('In a knowledge-based AI research assistant, which THREE qualities matter most to you?')
    .setHelpText('Select exactly 3.')
    .setChoiceValues([
      'Every claim backed by a real, citable source',
      'Accuracy — it never invents facts',
      'Depth in my specific domain',
      'Transparency — I can see how it reached the answer',
      'It says “I don’t know” when the evidence isn’t there',
      'Speed — it saves me real time',
      'Breadth — covers the whole field, not just famous papers',
      'Lets me explore connections (papers ↔ molecules ↔ experts)'])
    .setRequired(true);
  q3.setValidation(FormApp.createCheckboxValidation().requireSelectExactly(3).build());

  form.addCheckboxItem()
    .setTitle('A research AI would lose your trust immediately if it…')
    .setHelpText('Select all that apply.')
    .setChoiceValues([
      'Invented a citation or reference',
      'Gave an answer with no sources at all',
      'Presented a contested claim as settled fact',
      'Used non-peer-reviewed / blog sources without flagging them',
      'Couldn’t tell me what it’s not sure about'])
    .showOtherOption(true).setRequired(true);

  form.addScaleItem()
    .setTitle('Today, how much do you trust AI-generated answers when making a real research decision?')
    .setBounds(1,5).setLabels('Not at all','Completely').setRequired(true);

  // ---- Part B: the paper (new page) ----
  form.addPageBreakItem()
    .setTitle('One quick task — rate a real paper')
    .setHelpText(
      'Please open and skim this open-access paper (~5 min), then answer the last four questions.\n\n' +
      '“Flavor network and the principles of food pairing” — Ahn, Ahnert, Bagrow & Barabási, ' +
      'Scientific Reports (2011).\n' +
      'Link:  https://www.nature.com/articles/srep00196\n\n' +
      'It’s one of the most cited papers connecting food chemistry, aroma compounds and data science.');

  form.addScaleItem()
    .setTitle('As a source for a meaty-flavor knowledge base, how would you rate this paper overall?')
    .setBounds(1,10).setLabels('Not useful','Essential').setRequired(true);

  var q7 = form.addCheckboxItem()
    .setTitle('What did you weigh MOST in deciding that rating?')
    .setHelpText('Select up to 2.')
    .setChoiceValues([
      'Scientific rigor / methods',
      'Novelty of the idea',
      'Real-world applicability to flavor work',
      'How influential / highly-cited it is',
      'Data quality & reproducibility',
      'Clarity & how well it’s written',
      'Relevance to meaty flavor specifically',
      'How well its central claim is actually supported'])
    .setRequired(true);
  q7.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(2).build());

  form.addMultipleChoiceItem()
    .setTitle('This paper is highly cited — but its central “food-pairing” claim is debated ' +
      '(it fits Western cuisines, not Eastern, and later studies push back). Should an AI assistant cite it ' +
      'when answering a researcher?')
    .setChoiceValues([
      'Yes — it’s foundational',
      'Only with a caveat that the claim is debated',
      'No — too contested to cite as evidence'])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('In one sentence: when MeatCODE decides whether to include a paper like this, what should it prioritize most?')
    .setRequired(true);

  Logger.log('EDIT this form here:  ' + form.getEditUrl());
  Logger.log('SHARE (live) link:    ' + form.getPublishedUrl());
}
