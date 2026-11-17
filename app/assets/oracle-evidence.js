/* Updated 2026-11-17 · Real paper links and complete, per-source stance accounting. */
(function(root){
  'use strict';
  function safeURL(value){try{var u=new URL(String(value||''));return /^https?:$/.test(u.protocol)?u.href:'';}catch(e){return '';}}
  function paperURL(p){
    var doi=String(p.doi||'').trim().replace(/^(?:https?:\/\/)?(?:dx\.)?doi\.org\//i,'').replace(/^doi:\s*/i,'');
    return /^10\.\d{4,9}\//.test(doi)?'https://doi.org/'+encodeURI(doi):safeURL(p.url);
  }
  function consensus(sources,data){
    var map={}, counts={agree:0,oppose:0,neutral:0,unassessed:0};
    ((data&&Array.isArray(data.per_source))?data.per_source:[]).forEach(function(p){
      var stance=String(p.stance||'').toLowerCase(); if(stance==='support')stance='agree';
      if(['agree','oppose','neutral'].indexOf(stance)>=0)map[String(p.id)]=stance;
    });
    var seen={}, rows=[];
    (sources||[]).forEach(function(p){var id=String(p.id);if(seen[id])return;seen[id]=true;
      var stance=map[id]||'unassessed';counts[stance]++;rows.push({id:p.id,stance:stance});});
    return Object.assign(counts,{total:rows.length,per_source:rows,central_claim:String(data&&data.central_claim||'')});
  }
  function label(stance){return {agree:'Supports',oppose:'Opposes',neutral:'Neutral',unassessed:'Not assessed'}[stance]||'Not assessed';}
  var api={safeURL:safeURL,paperURL:paperURL,consensus:consensus,label:label};
  root.MCOracleEvidence=api;if(typeof module==='object'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
