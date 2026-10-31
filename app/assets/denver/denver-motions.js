(function(global){
'use strict';
const S=global.DenverSprite, K=S.keys,E=S.ease,C=S.clamp;
const motions={
 curious:{label:'Curious glances',duration:7200,loop:true,line:'Oh! What are you making?',purpose:'Quiet company while the user works.'},
 follow:{label:'Follow the pointer',duration:4800,loop:true,line:'Is that where we are going?',purpose:'Attend to the user with gentle, delayed eye movement.'},
 sleepy:{label:'Sleepy little blinks',duration:6000,loop:true,line:'I was just… resting my eyes.',purpose:'A soft idle after a quiet moment.'},
 hello:{label:'A shy hello',duration:3200,loop:false,line:'Hi… I’m Denver. Can I stay here?',purpose:'A cautious peek, followed by a tiny greeting.'},
 wave:{label:'One little wave',duration:2400,loop:false,line:'Oh! Hi again.',purpose:'A short greeting when the user returns.'},
 brave:{label:'A bit more courage',duration:3200,loop:false,line:'I made you a little note.',purpose:'A second peek after an intentional interaction.'},
 note:{label:'Offer a note',duration:1400,loop:false,line:'You can write it here. I’ll hold it.',purpose:'Lift the eyes, open the mouth, then unfold the input.'},
 oracle:{label:'Meet my creator',duration:3200,loop:false,line:'The Oracle made me. Want to make something together?',purpose:'Invite the user to the Oracle after they show interest.'},
 listening:{label:'Listen carefully',duration:3000,loop:true,line:'Mm-hm. I’m listening.',purpose:'Stay attentive while the user types.'},
 thinking:{label:'Wait with you',duration:3600,loop:true,line:'Let’s give the Oracle a little moment.',purpose:'Wait only while an actual request is pending.'},
 delighted:{label:'A tiny celebration',duration:2200,loop:false,line:'We did it! Look what you made!',purpose:'Celebrate a confirmed success, briefly.'},
 oops:{label:'A shy little oops',duration:2800,loop:false,line:'Oops. That didn’t work. Want to try again?',purpose:'Acknowledge a real error without blaming the user.'},
 again:{label:'Try together again',duration:2400,loop:false,line:'Okay. One more little try?',purpose:'Return to a ready pose after the user chooses retry.'},
 thanks:{label:'Thank you',duration:2600,loop:false,line:'You let me help. Thank you!',purpose:'A small grateful nod after the user completes an action.'},
 goodnight:{label:'Getting drowsy',duration:3600,loop:false,line:'I’ll be right here. Take your time.',purpose:'A quiet, optional sleepy state.'},
 tuck:{label:'Tuck away',duration:1800,loop:false,line:'Okay. See you in a little while.',purpose:'Respect dismissal and retreat without a prompt.'}
};
function pose(name,ms,options={}){
 const m=motions[name]||motions.curious,t=C(ms/m.duration),p={...S.sample('grip_rise',3360),bodyX:0,bodyY:0,lookX:0,lookY:0,lid:0,sx:1,sy:1,grip:1,grip2:1,handY:76,hand2Y:17,animateEyes:true,eyeLift:0,noteAmount:0,noteOpen:false,accent:null};
 p.lid=K(t,[[0,0],[.68,0],[.705,1],[.735,0],[1,0]]);
 if(name==='curious'){p.lookX=K(t,[[0,0],[.12,0],[.2,-1.5],[.38,-1.5],[.48,1.5],[.62,1.5],[.75,0],[1,0]]);p.lookY=K(t,[[0,-1],[.3,-2],[.5,-2],[.64,0],[.84,-1],[1,-1]]);p.bodyX=Math.round(Math.sin(t*Math.PI*2));}
 if(name==='follow'){p.lookX=options.lookX??Math.cos(t*Math.PI*2)*1.5;p.lookY=options.lookY??(-1+Math.sin(t*Math.PI*2)*2);}
 if(name==='sleepy'){p.lid=K(t,[[0,.18],[.28,.18],[.4,.8],[.52,.8],[.63,.2],[.85,.2],[1,.18]]);p.lookX=-1;p.lookY=-1;p.bodyY=Math.round(Math.sin(t*Math.PI)*1);}
 if(name==='hello'){p.bodyX=K(t,[[0,20],[.2,8],[.35,12],[.6,0],[1,0]]);p.hand2Y=17-3*Math.sin(C((t-.5)/.5)*Math.PI*3);p.lookY=-1;}
 if(name==='wave'){p.hand2Y=17-4*Math.sin(t*Math.PI*4)*Math.sin(t*Math.PI);p.lookY=-1;}
 if(name==='brave'){p.bodyX=K(t,[[0,10],[.25,5],[.4,8],[.7,0],[1,0]]);p.lookX=K(t,[[0,-1],[.4,-1],[.6,1],[1,0]]);}
 if(name==='note'){p.eyeLift=3*E(ms/220);p.noteAmount=E((ms-220)/220);p.noteOpen=p.noteAmount>0;p.lid=0;p.lookY=-1;}
 if(name==='oracle'){p.bodyY=-Math.round(Math.sin(t*Math.PI*2)*2);p.hand2Y=17-3*Math.sin(t*Math.PI);p.lookY=-2;p.accent='star';}
 if(name==='listening'){p.lookX=options.lookX??0;p.lookY=-1;p.bodyY=Math.round(Math.sin(t*Math.PI*2));}
 if(name==='thinking'){p.lookX=1;p.lookY=-1;p.accent='dots';}
 if(name==='delighted'){p.bodyY=-Math.round(Math.abs(Math.sin(t*Math.PI*3))*3*(1-t));p.hand2Y=17-2*Math.sin(t*Math.PI);p.accent='sparkles';}
 if(name==='oops'){p.bodyX=K(t,[[0,0],[.2,6],[.6,6],[1,0]]);p.lookX=-1;p.lookY=0;p.lid=.2;}
 if(name==='again'){p.bodyX=8*(1-E(t));p.lookY=-1;p.hand2Y=17-2*Math.sin(t*Math.PI*2);}
 if(name==='thanks'){p.bodyY=Math.round(Math.sin(t*Math.PI*2)*2);p.lookX=-Math.sin(t*Math.PI)*1.5;p.lookY=-1;}
 if(name==='goodnight'){p.lid=.65*E(t);p.bodyX=5*E(t);p.lookX=-1;p.lookY=-1;}
 if(name==='tuck'){p.bodyX=56*E(t/.75);p.grip=1-E((t-.65)/.35);p.grip2=1-E((t-.55)/.35);}
 if(options.still){p.bodyY=0;p.lid=0;p.lookX=0;p.lookY=-1;p.hand2Y=17;}
 return p;
}
function draw(ctx,name,ms,options={}){const p=pose(name,ms,options);S.draw(ctx,p);return p;}
global.DenverMotions={motions,pose,draw};
})(globalThis);
