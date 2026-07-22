/**
 * MeatCODE — "Help Us Build It, Together"  (FRIENDLY form + the important detailed questions restored)
 * Last updated: 2026-07-22 · Advisory · one-click Google Form generator
 *
 * Warm, plain-language flow — but the six questions you flagged as important are kept VERBATIM:
 *   1) the "three highest-priority capabilities" list,
 *   2) "which analytical-data functions would be most useful",
 *   3) "what would prevent you from sharing analytical data",
 *   4) the full "would you be interested in any of the following" list,
 *   5) "may we contact you for a short follow-up discussion" (with its branch),
 *   6) the Name / Organization / Email details.
 *
 * Order & fit:
 *   - The two analytical questions sit behind a one-tap "is lab work part of what you do?" gate,
 *     so people who don't do lab work never see them (keeps the form short for them).
 *   - "May we contact you?" branches: Yes/Maybe -> details page; No -> skips to the last page.
 *   - Friendly extras kept: newsletter-on-by-default (opt-out) and refer-a-friend.
 *
 * HOW TO USE (2 min):
 *   1. https://script.google.com  ->  New project.
 *   2. Delete the sample code, paste ALL of this file, then Save (Cmd+S).
 *   3. In the function dropdown pick  createFriendlyForm  ->  Run.
 *   4. Authorize with your own Google account. Open the Execution log for the EDIT + LIVE links.
 *      (To see the two lab questions while testing, answer "Yes" to the lab gate.)
 */

function createFriendlyForm() {
  var form = FormApp.create('MeatCODE — Help Us Build It, Together')
    .setProgressBar(true)
    .setCollectEmail(false);
  form.setDescription(
    'Hi, and thank you for being here.\n\n' +
    'MeatCODE is a free, open-source project from GFI Israel — a shared, science-backed home for ' +
    'everyone working on meaty flavor and aroma. Think of it as one place where the scattered science, ' +
    'molecules, aromas, methods, and people finally connect — and where every answer comes with its real ' +
    'source, so you can actually trust it.\n\n' +
    'Here is the part we love most: it is open. It is built in the open, free to use, and free to improve — ' +
    'anyone can see how it works and help make it better. So the things you tell us here do not vanish into ' +
    'a report. Your frustrations become the features. Your ideas can go straight into the tool.\n\n' +
    'This takes about 5 minutes, and there are no wrong answers — just tell us how you really work and what ' +
    'would genuinely help. (Please do not share anything confidential or proprietary.)\n\n' +
    'Excited to build this with you.\n' +
    '— The MeatCODE team · GFI Israel · danield@gfi.org');

  function mc(title, choices, o){ o=o||{}; var i=form.addMultipleChoiceItem().setTitle(title).setChoiceValues(choices);
    if(o.help)i.setHelpText(o.help); if(o.other)i.showOtherOption(true); if(o.required)i.setRequired(true); return i; }
  function cb(title, choices, o){ o=o||{}; var i=form.addCheckboxItem().setTitle(title).setChoiceValues(choices);
    if(o.help)i.setHelpText(o.help); if(o.other)i.showOtherOption(true); if(o.required)i.setRequired(true);
    if(o.atMost)i.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(o.atMost).build());
    if(o.exactly)i.setValidation(FormApp.createCheckboxValidation().requireSelectExactly(o.exactly).build()); return i; }
  function para(title, o){ o=o||{}; var i=form.addParagraphTextItem().setTitle(title);
    if(o.help)i.setHelpText(o.help); if(o.required)i.setRequired(true); return i; }

  // ===================== PAGE 1 — A little about you =====================
  form.addSectionHeaderItem().setTitle('First, a little about you')
    .setHelpText('Just so we can make sense of your answers — nothing more.');

  mc('Which of these sounds most like you?', [
    'A researcher or student',
    'Industry R&D or product developer',
    'Flavor or ingredient specialist',
    'Analytical or sensory scientist',
    'A funder, nonprofit, or ecosystem role'], {required:true, other:true});

  cb('What is closest to the world you work in?', [
    'Meat flavor and aroma chemistry',
    'Ingredients, precursors, and fermentation',
    'Plant-based, cultivated, or hybrid meat',
    'Analytical science (like GC-MS or LC-MS)',
    'Sensory and consumer science'], {required:true, other:true, help:'Pick any that fit.'});

  // ===================== PAGE 2 — How you work today =====================
  form.addPageBreakItem().setTitle('How you work today')
    .setHelpText('We are all fighting the same battle to find good, trustworthy science. Tell us about yours.');

  mc('How often do you go hunting for scientific or technical info in your work?', [
    'Most days','A few times a week','A few times a month','Now and then','Rarely'], {required:true});

  // >>> ADDED VERBATIM: which sources do you currently use <<<
  cb('Which sources do you currently use?', [
    'Scientific journal databases',
    'Google Scholar',
    'General web search',
    'Patents',
    'Colleagues or personal networks',
    'Conferences or webinars',
    'Flavor or ingredient suppliers',
    'General-purpose AI tools (ChatGPT, Gemini, Claude, Perplexity)',
    'Specialized scientific databases',
    'Internal company / analytical data'], {required:true, other:true, help:'Pick any you rely on.'});

  cb('When you are looking for reliable science, what frustrates you the most?', [
    'It is scattered everywhere and hard to pull together',
    'It is hard to tell what is actually trustworthy',
    'The good stuff is stuck behind paywalls',
    'AI tools make things up or cannot show their sources',
    'Reading and comparing studies takes forever',
    'It is hard to find the right person to ask'],
    {required:true, atMost:3, help:'Pick up to 3.'});

  para('Tell us about one thing in your work that is needlessly slow or frustrating — we might just build the fix.',
    {help:'Totally optional. Please keep it non-confidential.'});

  // ===================== PAGE 3 — Meet MeatCODE =====================
  form.addPageBreakItem().setTitle('Meet MeatCODE')
    .setHelpText(
      'So what is MeatCODE, really?\n\n' +
      'Imagine everything known about meaty flavor — the papers, the molecules and aromas, the reactions, ' +
      'the methods, and the people — all in one connected place, where every answer shows you the real ' +
      'science behind it (no making things up).\n\n' +
      'It is free, and it is open: anyone can use it, see how it works, and help improve it. When you ' +
      'suggest something, it can go straight into the tool — so this is not a company product being sold ' +
      'to you, it is a shared resource you get to help build.\n\n' +
      'The first version will not predict flavors for you. Its job is simpler and more useful: make the ' +
      'science, methods, and people you already need far easier to find, trust, and use.');

  mc('Had you come across MeatCODE before today?', [
    'Yes — I know what it is about','I had heard the name','Only a little','No, this is new to me'],
    {required:true});

  form.addScaleItem().setTitle('Honestly — does this sound like something you would use?')
    .setBounds(1, 5).setLabels('Not really','Yes, I want this').setRequired(true);

  mc('What would you most want it for?', [
    'Finding and trusting the science faster',
    'Exploring molecules, aromas, and how they connect',
    'Making sense of analytical data',
    'Finding methods, protocols, and benchmarks',
    'Finding the right people and collaborators'], {required:true, other:true});

  // ===================== PAGE 4 — What should we build first =====================
  form.addPageBreakItem().setTitle('What should we build first?')
    .setHelpText('Because MeatCODE is open, what you pick here genuinely decides what we build first. So choose what you would truly love to have.');

  // >>> RESTORED VERBATIM: the three-highest-priority capabilities list <<<
  cb('Which three capabilities should be the highest priority in the first usable MeatCODE release?', [
    'Source-backed literature search and evidence summaries',
    'An Oracle that answers technical questions with traceable citations',
    'Molecular and mechanistic database',
    'Links between precursors, reactions, volatiles, sensory descriptors, and methods',
    'Expert and organization directory',
    'Protocols, methods, and experimental templates',
    'Benchmarking frameworks and reference systems',
    'Analytical-data comparison and visualization',
    'Research-gap / white-space maps',
    'Community contribution and expert-review functions'],
    {required:true, exactly:3, help:'Select exactly three.'});

  cb('For you to actually trust an answer from MeatCODE, what matters most?', [
    'I can click straight through to the real source',
    'It is clear how strong the evidence is',
    'It is honest when it does not know',
    'An expert has checked it',
    'I can see the conditions behind a result',
    'It shows more than one source'],
    {required:true, atMost:3, help:'Pick up to 3.'});

  para('If you could ask MeatCODE one real question right now, what would it be?',
    {help:'Optional — but a great way to help us get it right. Please keep it non-confidential.'});

  // Lab gate (last item on this page) — "No" skips the two lab questions.
  var gateLab = form.addMultipleChoiceItem()
    .setTitle('Last check before the next part: is molecular or analytical (lab) work part of what you do?')
    .setHelpText('If not, no problem — we will skip the next two lab-focused questions.')
    .setRequired(true);

  // ===================== PAGE 5 — A couple of lab questions (gated) =====================
  form.addPageBreakItem().setTitle('A couple of lab questions')
    .setHelpText('Just for people doing analytical / lab work — thank you for the detail.');

  // >>> RESTORED VERBATIM: analytical-data functions <<<
  cb('Which analytical-data functions would be most useful?', [
    'Upload standardized GC-MS data',
    'Compare samples against reference profiles',
    'Compare raw vs cooked samples',
    'Compare animal vs alternative-meat samples',
    'Compare cooking conditions',
    'Visualize heatmaps',
    'PCA / exploratory analysis',
    'Identify missing or enriched compounds',
    'Connect compounds to odor / sensory descriptors',
    'Export standardized datasets'], {other:true, atMost:5, help:'Select up to five.'});

  // >>> RESTORED VERBATIM: barriers to sharing analytical data <<<
  cb('What would prevent you from sharing analytical data? (optional)', [
    'Confidentiality / IP concerns',
    'Client or publication restrictions',
    'Lack of standardized data formats',
    'Concern about incorrect cross-lab comparison',
    'Time required to prepare data',
    'Unclear ownership or licensing',
    'I would not share analytical data'], {other:true});

  // ===================== PAGE 6 — Let's build this together =====================
  var pbStaying = form.addPageBreakItem().setTitle('Let’s build this together')
    .setHelpText('That is it — thank you, really. Because MeatCODE is open and free, your answers here genuinely shape it. Just a few last, optional things.');

  // >>> RESTORED VERBATIM: full participation list <<<
  cb('Would you be interested in any of the following?', [
    'Beta testing the platform',
    'Testing the Oracle with real questions',
    'Reviewing scientific content',
    'Contributing public datasets or protocols',
    'Participating in an expert interview',
    'Joining a technical working session',
    'Advising on industry use cases',
    'Joining an advisory or expert council',
    'Receiving project updates',
    'Exploring a research collaboration'], {other:true});

  // Friendly extras (kept): newsletter on by default (opt-out) + refer a friend.
  cb('Staying in the loop', ['No thanks — please do not send me updates'],
    {help:'By default we will send you the occasional MeatCODE update — and because it is built in the open, you will actually see your ideas show up. Unsubscribe anytime, or tick the box to skip it.'});

  para('Know someone who would love this? Share their name or email and we will reach out kindly.',
    {help:'Optional — only people you think would genuinely be glad to hear about it.'});

  // ===================== PAGE 7 — Follow-up (branch) =====================
  form.addPageBreakItem().setTitle('Follow-up');
  // >>> RESTORED VERBATIM: may we contact you (with branch) <<<
  var qContact = form.addMultipleChoiceItem()
    .setTitle('May we contact you for a short follow-up discussion?').setRequired(true);

  // ===================== PAGE 8 — Your details (only if Yes/Maybe) =====================
  var pbDetails = form.addPageBreakItem().setTitle('Your details')
    .setHelpText('Only shown because you agreed to a follow-up. Used solely to contact you about MeatCODE.');
  form.addTextItem().setTitle('Name').setRequired(true);
  form.addTextItem().setTitle('Organization');
  form.addTextItem().setTitle('Email address').setRequired(true)
    .setValidation(FormApp.createTextValidation().setHelpText('Please enter a valid email address.').requireTextIsEmail().build());

  // ===================== PAGE 9 — One last thing (convergence) =====================
  var pbFinal = form.addPageBreakItem().setTitle('One last thing');
  para('Anything else on your mind?', {});

  // ---- wire up the branches (targets now exist) ----
  gateLab.setChoices([
    gateLab.createChoice('Yes', FormApp.PageNavigationType.CONTINUE),
    gateLab.createChoice('No', pbStaying)]);
  qContact.setChoices([
    qContact.createChoice('Yes', pbDetails),
    qContact.createChoice('Maybe, depending on the topic', pbDetails),
    qContact.createChoice('No', pbFinal)]);

  form.setConfirmationMessage(
    'Thank you — truly.\n\n' +
    'You have just helped shape something open and free that the whole field can use. Because MeatCODE is ' +
    'built in the open, the things you told us here go straight into what we build next. If you left your ' +
    'email, we will keep you posted — and you will see your ideas show up.\n\n' +
    'See you inside.\n— The MeatCODE team, GFI Israel');

  try {
    var ss = SpreadsheetApp.create('MeatCODE — Responses (friendly form)');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
    Logger.log('Responses sheet: ' + ss.getUrl());
  } catch (e) { Logger.log('Could not auto-create responses sheet (link it manually in Responses tab): ' + e); }

  Logger.log('EDIT this form:  ' + form.getEditUrl());
  Logger.log('LIVE (share):    ' + form.getPublishedUrl());
}
