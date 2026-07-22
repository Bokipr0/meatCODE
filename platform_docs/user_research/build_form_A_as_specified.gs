/**
 * MeatCODE — User Needs & MVP Validation Questionnaire
 * FORM A — "AS SPECIFIED": a faithful build of the brief (all 30 questions, 7 sections).
 * Last updated: 2026-07-22 · Advisory · one-click Google Form generator
 *
 * HOW TO USE (2 min):
 *   1. https://script.google.com  →  New project.
 *   2. Delete the sample code, paste ALL of this file, then Save (Cmd+S).
 *   3. In the function dropdown (top toolbar) pick  createFormA_AsSpecified  →  Run.
 *   4. Authorize with your own Google account. Open the Execution log for the EDIT + LIVE links.
 *
 * TWO FILES, TWO PROJECTS: keep Form A and Form B in SEPARATE Apps Script projects
 * (all helpers here are nested inside the function, so nothing collides even if you don't).
 *
 * BRANCHING REALITY: Google Forms can only branch from multiple-choice/dropdown questions,
 * section to section. Role-based gating of Section 6 (as the brief describes it) is NOT
 * natively possible from checkbox answers, so Section 6 opens with a single yes/no relevance
 * gate — the closest feasible equivalent. The AI-usage (Q17) and follow-up (Q25) branches
 * work exactly as specified.
 */

function createFormA_AsSpecified() {
  var form = FormApp.create('MeatCODE User Needs & MVP Validation Questionnaire — v1 (as specified)')
    .setProgressBar(true)
    .setCollectEmail(false);
  form.setDescription(
    'MeatCODE — the Meat Collaborative Open Development Ecosystem — is a GFI Israel-led, open and pre-competitive initiative intended to make meaty-flavor R&D more systematic, evidence-based, and collaborative.\n\n' +
    'MeatCODE is being developed as a source-backed R&D hub connecting scientific literature, molecules, reaction pathways, sensory descriptors, analytical methods, experts, organizations, protocols, datasets, and practical research tools.\n\n' +
    'This questionnaire will help us understand how researchers and industry professionals currently work, where they encounter friction, and which MeatCODE capabilities would provide the greatest practical value. It should take approximately 5–10 minutes.\n\n' +
    'Responses will be used to prioritize the MeatCODE MVP, improve its user journeys, and identify potential beta testers, contributors, advisors, and collaborators.\n\n' +
    'Please do not include confidential, proprietary, unpublished, or commercially sensitive information in your answers.\n\n' +
    'Contact: Daniel Dikovsky · GFI Israel SciTech · danield@gfi.org');

  // ---- inner helpers (scoped to this function; no cross-file collisions) ----
  function mc(title, choices, o){ o=o||{}; var i=form.addMultipleChoiceItem().setTitle(title).setChoiceValues(choices);
    if(o.help)i.setHelpText(o.help); if(o.other)i.showOtherOption(true); if(o.required)i.setRequired(true); return i; }
  function cb(title, choices, o){ o=o||{}; var i=form.addCheckboxItem().setTitle(title).setChoiceValues(choices);
    if(o.help)i.setHelpText(o.help); if(o.other)i.showOtherOption(true); if(o.required)i.setRequired(true);
    if(o.atMost)i.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(o.atMost).build());
    if(o.exactly)i.setValidation(FormApp.createCheckboxValidation().requireSelectExactly(o.exactly).build()); return i; }
  function para(title, o){ o=o||{}; var i=form.addParagraphTextItem().setTitle(title);
    if(o.help)i.setHelpText(o.help); if(o.required)i.setRequired(true); return i; }

  var CAPS12 = [
    'Source-backed literature search and evidence summaries',
    'An Oracle that answers technical questions with traceable citations',
    'Molecular and mechanistic database',
    'Links between precursors, reactions, volatiles, sensory descriptors, and methods',
    'Expert and organization directory',
    'Protocols, methods, and experimental templates',
    'Benchmarking frameworks and reference systems',
    'Analytical-data comparison and visualization',
    'Research-gap and white-space maps',
    'Community contribution and expert-review functions',
    'Private project workspaces',
    'APIs or data export'];
  var CAPS10 = CAPS12.slice(0, 10); // Q14: omit private workspaces + APIs (tightly-focused first release)

  // ================= SECTION 1 — RESPONDENT PROFILE =================
  form.addSectionHeaderItem().setTitle('Section 1 — Respondent profile');

  mc('Which option best describes your current role?', [
    'Academic researcher','Industry R&D scientist','Product developer or formulator','Flavorist',
    'Ingredient developer or supplier','Analytical scientist','Sensory scientist','Meat scientist',
    'Fermentation or biotechnology researcher','Data scientist, computational scientist, or AI specialist',
    'Research manager or R&D leader','Funder, program manager, or ecosystem organization',
    'Consultant or independent expert','Student or early-career researcher'], {required:true, other:true});

  mc('What type of organization do you primarily work in?', [
    'University or academic research institute','Alternative-protein company','Food manufacturer',
    'Flavor company','Ingredient company','Analytical or sensory service provider',
    'Biotechnology or fermentation company','Nonprofit or ecosystem organization',
    'Government or public research organization','Funding organization','Independent or consulting'],
    {required:true, other:true});

  cb('Which areas are relevant to your work?', [
    'Meat flavor chemistry','Maillard or Strecker chemistry','Lipid chemistry and lipid oxidation',
    'Protein hydrolysis, peptides, or amino acids','Fermentation or precision fermentation',
    'Yeast extracts or savory ingredients','Food matrix design','Flavor release or delivery',
    'Plant-based meat formulation','Blended or hybrid meat products','Cultivated meat',
    'Analytical chemistry','GC-MS or GC-O','LC-MS, metabolomics, or proteomics','Lipidomics',
    'Sensory science','Consumer research','Computational modeling or AI','Research strategy or funding'],
    {required:true, other:true});

  mc('How many years of relevant professional or research experience do you have?', [
    'Less than 2 years','2–5 years','6–10 years','11–20 years','More than 20 years'], {});

  // ================= SECTION 2 — CURRENT WORKFLOWS AND PAIN POINTS =================
  form.addPageBreakItem().setTitle('Section 2 — Current workflows and pain points');

  mc('In your current work, how often do you search for scientific or technical information related to meat flavor, aroma, sensory performance, ingredients, or analytical methods?', [
    'Daily','Several times per week','Several times per month','Occasionally','Rarely','Never'], {required:true});

  cb('Which sources do you currently use?', [
    'Scientific journal databases','Google Scholar','General web search','Patents',
    'Internal company databases','Colleagues or personal networks','Conferences or webinars',
    'Flavor or ingredient suppliers','Consultants',
    'General-purpose AI tools such as ChatGPT, Gemini, Claude, or Perplexity',
    'Specialized scientific databases','Internal analytical or sensory data'], {required:true, other:true});

  cb('What are the most difficult parts of finding or using relevant knowledge?', [
    'Relevant literature is scattered across disciplines','Important information is behind paywalls',
    'It is difficult to judge evidence quality','Studies use inconsistent terminology',
    'Experimental conditions are difficult to compare',
    'Molecule, pathway, sensory, and formulation data are disconnected',
    'Analytical data are difficult to interpret','Patent information is difficult to navigate',
    'Applied knowledge is proprietary','General-purpose AI answers are insufficiently reliable',
    'General-purpose AI answers lack traceable sources','It is difficult to find the right expert or collaborator',
    'Existing protocols are incomplete or difficult to reproduce',
    'It is difficult to translate academic findings into product development',
    'I do not experience major difficulties'], {required:true, other:true, atMost:5, help:'Select up to five.'});

  cb('Which tasks consume the most time or involve the most repeated effort?', [
    'Literature searching','Reviewing and summarizing papers','Comparing conflicting scientific claims',
    'Identifying relevant molecules or precursors','Connecting molecules to sensory descriptors',
    'Identifying reaction pathways','Comparing analytical datasets','Selecting analytical methods',
    'Designing experiments','Finding benchmark or reference systems','Finding experts or collaborators',
    'Identifying research gaps','Translating science into formulation hypotheses',
    'Preparing technical reviews or presentations'], {other:true, atMost:5, help:'Select up to five.'});

  para('Describe one recurring question or task that is currently difficult, slow, or poorly supported.',
    {help:'Please describe the task without including confidential formulations, proprietary data, unpublished results, or commercially sensitive details.'});

  // ================= SECTION 3 — INITIAL REACTION TO MEATCODE =================
  form.addPageBreakItem().setTitle('Section 3 — Initial reaction to MeatCODE')
    .setHelpText('MeatCODE is envisioned as a source-backed research environment that connects several types of knowledge and tools. The first version will not be a validated flavor-prediction engine. Its purpose is to make existing evidence, methods, people, and research options easier to navigate and use.');

  mc('Before receiving this questionnaire, had you heard of MeatCODE?', [
    'Yes, and I understand the concept','Yes, but only at a high level','I had heard the name','No'], {required:true});

  form.addScaleItem().setTitle('How relevant is the overall MeatCODE concept to your work?')
    .setBounds(1, 5).setLabels('Not relevant','Highly relevant').setRequired(true);

  mc('What would be your main reason for using MeatCODE?', [
    'Find and understand scientific evidence',
    'Explore molecules, precursors, pathways, and sensory associations',
    'Interpret or compare analytical data','Find protocols, methods, and benchmark systems',
    'Find experts or organizations','Generate or refine research questions','Design experiments',
    'Support product-development decisions','Identify white spaces or funding opportunities',
    'Teach or onboard colleagues or students','I am not currently likely to use it'], {required:true, other:true});

  // ================= SECTION 4 — PRIORITIZATION OF MVP CAPABILITIES =================
  form.addPageBreakItem().setTitle('Section 4 — Prioritization of MVP capabilities');

  form.addGridItem().setTitle('How valuable would each MeatCODE capability be for your work?')
    .setRows(CAPS12)
    .setColumns(['No value','Low value','Moderate value','High value','Essential','Not relevant to my work'])
    .setRequired(true);

  cb('Which three capabilities should receive the highest priority in the first usable MeatCODE release?',
    CAPS10, {required:true, exactly:3, help:'Select exactly three.'});

  mc('Which capability should not be prioritized yet?', [
    'Predictive flavor modeling','Automated formulation recommendations','Community discussion features',
    'Private notebooks or workspaces','APIs','Large-scale analytical-data upload','Expert matching',
    'None — all are near-term priorities'], {other:true});

  cb('What minimum level of evidence or transparency would you need before relying on MeatCODE for an R&D decision?', [
    'Links to original sources',
    'Clear distinction between peer-reviewed evidence, patents, expert opinion, and hypotheses',
    'Evidence-quality or confidence labels','Visibility of experimental conditions',
    'Ability to inspect the extracted source text or data','Multiple independent sources','Expert review',
    'Reproducible protocols','Analytical validation','Sensory validation',
    'Comparison with established tools or databases'], {required:true, other:true});

  // ================= SECTION 5 — ORACLE AND AI-SUPPORTED RESEARCH =================
  form.addPageBreakItem().setTitle('Section 5 — Oracle and AI-supported research')
    .setHelpText('The MeatCODE Oracle is intended to answer technical questions using the structured MeatCODE evidence base and provide traceable sources. It should complement, rather than merely duplicate, general-purpose AI tools.');

  var q17 = form.addMultipleChoiceItem()
    .setTitle('How often do you currently use general-purpose AI tools for scientific or technical work?')
    .setRequired(true);

  form.addPageBreakItem().setTitle('General-purpose AI tools — your experience');
  cb('What limitations have you experienced when using general-purpose AI tools for this work?', [
    'Fabricated or incorrect references','Weak source traceability','Answers are too general',
    'Insufficient domain depth','Failure to distinguish strong evidence from speculation',
    'Poor understanding of experimental conditions','Inability to use proprietary or internal data safely',
    'Difficulty reproducing the reasoning or result','No major limitations'], {other:true});

  var pbOracle = form.addPageBreakItem().setTitle('The MeatCODE Oracle');
  cb('Which Oracle functions would make it meaningfully better than a general-purpose AI assistant?', [
    'Answers restricted to a curated evidence base','Direct citations to source material',
    'Evidence-strength and confidence labels','Structured comparison of conflicting studies',
    'Connections between papers, molecules, methods, and sensory outcomes',
    'Ability to filter by meat species, matrix, process, temperature, or analytical method',
    'Ability to show data tables rather than only narrative answers','Suggested follow-up questions',
    'Suggested experimental designs','Clear indication when evidence is insufficient','Expert-reviewed answers'],
    {required:true, other:true, atMost:5, help:'Select up to five.'});

  para('Please provide one real, non-confidential question you would use to test the MeatCODE Oracle.',
    {help:'Examples could involve a precursor, pathway, analytical method, sensory descriptor, matrix effect, benchmark comparison, or experimental design.'});

  // Q17 branch: "Never" jumps past the limitations page straight to the Oracle page.
  q17.setChoices([
    q17.createChoice('Daily', FormApp.PageNavigationType.CONTINUE),
    q17.createChoice('Several times per week', FormApp.PageNavigationType.CONTINUE),
    q17.createChoice('Several times per month', FormApp.PageNavigationType.CONTINUE),
    q17.createChoice('Occasionally', FormApp.PageNavigationType.CONTINUE),
    q17.createChoice('Never', pbOracle)]);

  // ================= SECTION 6 — MOLECULAR DATABASE AND ANALYTICAL TOOLS =================
  form.addPageBreakItem().setTitle('Section 6 — Molecular database and analytical tools')
    .setHelpText('These questions are most relevant to scientific, analytical, formulation, flavor, or ingredient roles.');
  var gate6 = form.addMultipleChoiceItem()
    .setTitle('Are molecular databases and/or analytical tools (e.g. GC-MS) relevant to your work?')
    .setRequired(true);

  form.addPageBreakItem().setTitle('Molecular and analytical tools');
  cb('Which information should a molecular and mechanistic database connect?', [
    'Precursors','Amino acids and peptides','Sugars','Nucleotides','Vitamins and cofactors',
    'Lipids and fatty acids','Volatile compounds','Non-volatile taste compounds','Sensory descriptors',
    'Odor thresholds','Reaction pathways','Cooking conditions','Food matrices','Analytical methods',
    'GC-MS retention or spectral information','Evidence sources','Commercial or natural ingredient sources',
    'Safety or regulatory information'], {other:true});

  cb('Which analytical-data functions would be most useful?', [
    'Upload standardized GC-MS data','Compare samples against reference profiles',
    'Compare raw and cooked samples','Compare animal meat and alternative-meat samples',
    'Compare cooking conditions','Compare aqueous and lipid fractions','Visualize heatmaps',
    'Perform PCA or other exploratory analysis','Identify missing or enriched compounds',
    'Connect compounds to odor or sensory descriptors','Apply data-quality checks',
    'Export standardized datasets','None of these are relevant to my work'],
    {other:true, atMost:5, help:'Select up to five.'});

  cb('What would prevent you from uploading or sharing analytical data?', [
    'Confidentiality','Intellectual-property concerns','Client restrictions','Publication restrictions',
    'Lack of standardized data formats','Concern about incorrect comparison across laboratories',
    'Time required for data preparation','Unclear ownership or licensing','Data-quality concerns',
    'No barrier','I would not upload analytical data'], {other:true});

  // ================= SECTION 7 — PARTICIPATION AND FOLLOW-UP =================
  var pbSection7 = form.addPageBreakItem().setTitle('Section 7 — Participation and follow-up');
  cb('Would you be interested in participating in any of the following?', [
    'Beta testing the MeatCODE platform','Testing the Oracle with real questions','Reviewing scientific content',
    'Reviewing molecular or analytical database structure','Contributing public datasets or protocols',
    'Participating in an expert interview','Joining a technical working session','Advising on industry use cases',
    'Joining an advisory or expert council','Receiving project updates','Exploring a research collaboration',
    'Not at this stage'], {other:true});

  form.addPageBreakItem().setTitle('Follow-up');
  var q25 = form.addMultipleChoiceItem()
    .setTitle('May we contact you for a short follow-up discussion?').setRequired(true);

  var pbContact = form.addPageBreakItem().setTitle('Your details')
    .setHelpText('Only shown because you agreed to a follow-up. We will use these details solely to contact you about MeatCODE.');
  form.addTextItem().setTitle('Name').setRequired(true);
  form.addTextItem().setTitle('Organization');
  form.addTextItem().setTitle('Email address').setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());
  form.addTextItem().setTitle('LinkedIn profile or professional webpage');

  var pbFinal = form.addPageBreakItem().setTitle('Final comments');
  para('Is there anything important we did not ask?', {});

  // Section 6 gate: "No" skips the molecular/analytical pages, jumps to Section 7.
  gate6.setChoices([
    gate6.createChoice('Yes', FormApp.PageNavigationType.CONTINUE),
    gate6.createChoice('No', pbSection7)]);
  // Q25 branch: Yes/Maybe → contact details; No → final comments.
  q25.setChoices([
    q25.createChoice('Yes', pbContact),
    q25.createChoice('Maybe, depending on the topic', pbContact),
    q25.createChoice('No', pbFinal)]);

  form.setConfirmationMessage(
    'Thank you for contributing to MeatCODE.\n\n' +
    'Your feedback will help us prioritize the first usable version of the platform and focus development on real scientific and product-development needs.\n\n' +
    'Please do not send confidential or proprietary information through this form. Where you indicated interest in further participation, the MeatCODE team may contact you regarding beta testing, expert interviews, advisory discussions, or collaboration opportunities.');

  // Linked responses sheet (form-building note #9) — one column per question, no merging.
  try {
    var ss = SpreadsheetApp.create('MeatCODE Questionnaire — Responses (Form A · as specified)');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
    Logger.log('Responses sheet: ' + ss.getUrl());
  } catch (e) { Logger.log('Could not auto-create responses sheet (link it manually in Responses tab): ' + e); }

  Logger.log('FORM A — EDIT this form:  ' + form.getEditUrl());
  Logger.log('FORM A — LIVE (share):    ' + form.getPublishedUrl());
}
