/* Last updated: 2026-10-30 · Codex · Deterministic editable pixel rig and motion library. */
(function (global) {
  'use strict';
  const W = 96, H = 96;
  const palette = { outline:'#39070b', rim:'#701015', red:'#d62026', light:'#ff2029', eye:'#fff7e7' };
  const motions = {
    idle:{label:'Breathe',duration:2400,loop:true},
    blink:{label:'Blink',duration:1100,loop:false},
    look:{label:'Look around',duration:2000,loop:false},
    wave:{label:'Say hello',duration:1800,loop:false},
    peek:{label:'Shy peek',duration:2600,loop:false},
    curious:{label:'Second look',duration:3400,loop:false},
    hop:{label:'Hop out',duration:1500,loop:false},
    land:{label:'Soft landing',duration:650,loop:false},
    retreat:{label:'Tuck away',duration:900,loop:false},
    sleep:{label:'Sleepy',duration:3000,loop:true},
    grip_lean:{label:'Hold & lean',duration:4200,loop:false},
    grip_pull:{label:'Two-hand pull',duration:4800,loop:false},
    grip_shy:{label:'Shy side-look',duration:4600,loop:false},
    grip_sideways:{label:'A · Edge-parallel peek',duration:4600,loop:false},
    grip_swing:{label:'B · Closer look',duration:4400,loop:false},
    grip_rise:{label:'C · Shy double-take',duration:4800,loop:false}
  };
  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
  const ease=t=>{t=clamp(t);return t*t*(3-2*t);};
  function keys(t, points) {
    if(t<=points[0][0]) return points[0][1];
    for(let i=1;i<points.length;i++) if(t<=points[i][0]) {
      const [a,x]=points[i-1],[b,y]=points[i];return x+(y-x)*ease((t-a)/(b-a));
    }
    return points[points.length-1][1];
  }
  function sample(name, ms) {
    const m=motions[name]||motions.idle, t=clamp(ms/m.duration);
    const p={sx:1,sy:1,dy:0,lookX:0,lookY:0,lid:0,wave:0,mouth:'smile',edge:0,foot:0};
    if(name==='idle') {p.sy=1-.025*Math.sin(t*Math.PI*2);p.sx=1+.012*Math.sin(t*Math.PI*2);}
    if(name==='blink') p.lid=keys(t,[[0,0],[.3,0],[.4,1],[.47,1],[.58,0],[1,0]]);
    if(name==='look') {p.lookX=keys(t,[[0,0],[.2,-2],[.45,-2],[.7,2],[.85,2],[1,0]]);p.lookY=-1;}
    if(name==='wave') {p.wave=keys(t,[[0,0],[.18,1],[.28,.65],[.4,1],[.52,.65],[.64,1],[.82,1],[1,0]]);p.mouth='happy';}
    if(name==='peek'||name==='curious') {
      p.edge=keys(t,name==='peek'?[[0,1.04],[.14,1.04],[.38,.52],[.72,.52],[1,1.04]]:[[0,1.04],[.1,1.04],[.27,.6],[.4,.6],[.52,.44],[.76,.44],[1,1.04]]);
      p.lookX=-2;p.lookY=keys(t,[[0,0],[.35,0],[.5,-1],[.7,1],[1,0]]);
      p.wave=keys(t,[[0,0],[.3,.35],[.7,.35],[1,0]]);
      p.lid=keys(t,[[0,0],[.56,0],[.59,1],[.63,0],[1,0]]);
    }
    if(name==='hop') {
      p.edge=keys(t,[[0,.52],[.15,.52],[.6,0],[1,0]]);
      p.sy=keys(t,[[0,1],[.15,.82],[.28,1.08],[.58,1.02],[.7,.82],[.84,1.03],[1,1]]);
      p.sx=keys(t,[[0,1],[.15,1.07],[.3,.96],[.6,1],[.7,1.09],[1,1]]);
      p.dy=-10*Math.sin(clamp((t-.16)/.52)*Math.PI);
      p.wave=.5*Math.sin(t*Math.PI);p.foot=Math.sin(t*Math.PI)*2;p.mouth='happy';
    }
    if(name==='land') {p.sy=keys(t,[[0,1],[.25,.8],[.6,1.04],[1,1]]);p.sx=keys(t,[[0,1],[.25,1.09],[.6,.98],[1,1]]);}
    if(name==='retreat') {p.edge=keys(t,[[0,0],[.15,0],[1,1.04]]);p.lookX=-1;p.wave=Math.sin(t*Math.PI)*.6;}
    if(name==='sleep') {p.lid=.7;p.sy=1-.02*Math.sin(t*Math.PI*2);p.mouth='sleep';}
    if(name.startsWith('grip_')) {
      p.gripping=true;p.edge=.40;p.sx=1;p.sy=1;p.lookX=-2;
      p.grip=keys(t,[[0,0],[.06,0],[.16,1],[.86,1],[.98,0],[1,0]]);
      p.grip2=name==='grip_pull'?keys(t,[[0,0],[.12,0],[.24,1],[.83,1],[.94,0],[1,0]]):0;
      p.bodyX=keys(t,[[0,72],[.19,72],[.43,name==='grip_pull'?-6:4],[.72,name==='grip_pull'?-6:4],[.90,72],[1,72]]);
      p.tilt=keys(t,[[0,0],[.22,0],[.44,name==='grip_lean'?.24:.12],[.7,name==='grip_lean'?.24:.12],[.9,0],[1,0]]);
      if(name==='grip_pull'){p.dy=keys(t,[[0,0],[.3,0],[.43,-4],[.55,-2],[.7,-4],[.9,0],[1,0]]);p.mouth='happy';}
      if(name==='grip_shy'){
        p.bodyX=keys(t,[[0,72],[.19,72],[.36,17],[.46,17],[.55,28],[.63,7],[.76,7],[.91,72],[1,72]]);
        p.tilt=keys(t,[[0,0],[.3,.1],[.45,.25],[.56,.1],[.7,.27],[.9,0],[1,0]]);
      }
      p.lookY=keys(t,[[0,0],[.4,-1],[.56,1],[.7,0],[1,0]]);
      p.lid=keys(t,[[0,0],[.6,0],[.625,1],[.66,0],[1,0]]);
    }
    if(['grip_sideways','grip_swing','grip_rise'].includes(name)){
      // Rotate the shared reference silhouette rigidly: never substitute a slimmer side drawing.
      p.parallelPose=true;p.upperOnly=true;p.testPose=false;p.tilt=0;p.bodyY=0;
      p.grip2=name==='grip_sideways'?0:keys(t,[[0,0],[.12,0],[.24,1],[.83,1],[.94,0],[1,0]]);
      p.handY=72;p.hand2Y=17;p.lookX=0;p.lookY=0;p.lid=0;p.sx=1;p.sy=1;
      p.bodyX=keys(t,[[0,56],[.19,56],[.43,0],[.75,0],[.92,56],[1,56]]);
      if(name==='grip_swing'){
        p.bodyX=keys(t,[[0,56],[.18,56],[.38,5],[.52,-2],[.75,-2],[.92,56],[1,56]]);
        p.lookY=keys(t,[[0,0],[.45,-1],[.62,1],[.75,0],[1,0]]);
      }
      if(name==='grip_rise'){
        p.bodyX=keys(t,[[0,56],[.18,56],[.36,6],[.46,6],[.54,20],[.67,0],[.77,0],[.93,56],[1,56]]);
      }
      p.lid=keys(t,[[0,0],[.61,0],[.635,1],[.67,0],[1,0]]);
    }
    return p;
  }
  function polygon(ctx, points, color) {
    ctx.fillStyle=color;
    const min=Math.floor(Math.min(...points.map(p=>p[1]))), max=Math.ceil(Math.max(...points.map(p=>p[1])));
    // Scan-line fill keeps every edge on the logical pixel grid, with no antialiasing.
    for(let y=min;y<max;y++) {
      const xs=[];
      for(let i=0,j=points.length-1;i<points.length;j=i++) {
        const [ax,ay]=points[i],[bx,by]=points[j];
        if((ay>y+.5)!==(by>y+.5)) xs.push(ax+(y+.5-ay)*(bx-ax)/(by-ay));
      }
      xs.sort((a,b)=>a-b);
      for(let i=0;i<xs.length;i+=2) ctx.fillRect(Math.ceil(xs[i]-.5),y,Math.ceil(xs[i+1]-.5)-Math.ceil(xs[i]-.5),1);
    }
  }
  // Reference image coordinates, uniformly mapped to the logical pixel grid.
  const ref=points=>points.map(([x,y])=>[48+(x-875)/18,13+(y-126)/18]);
  const shape=ref([[618,126],[1134,126],[1134,152],[1210,152],[1210,179],[1285,179],[1285,205],[1344,205],[1344,231],[1386,231],[1386,257],[1431,257],[1431,280],[1456,280],[1456,307],[1482,307],[1482,333],[1509,333],[1509,370],[1534,370],[1534,417],[1560,417],[1560,553],[1534,553],[1534,605],[1508,605],[1508,632],[1455,632],[1455,657],[1407,657],[1407,681],[1344,681],[1344,727],[1255,727],[1255,746],[598,746],[598,727],[408,727],[408,702],[345,702],[345,680],[295,680],[295,655],[269,655],[269,630],[242,630],[242,604],[215,604],[215,552],[190,552],[190,457],[216,457],[216,370],[242,370],[242,333],[269,333],[269,306],[295,306],[295,280],[320,280],[320,255],[364,255],[364,231],[408,231],[408,205],[466,205],[466,179],[539,179],[539,152],[618,152]]);
  function draw(ctx, pose={}) {
    const p={sx:1,sy:1,dy:0,lookX:0,lookY:0,lid:0,wave:0,mouth:'smile',foot:0,...pose};
    ctx.clearRect(0,0,W,H);ctx.imageSmoothingEnabled=false;
    ctx.save();
    const boundary=Math.round(W*(1-(p.edge||0)));
    if(p.gripping){ctx.beginPath();ctx.rect(0,0,boundary,H);ctx.clip();}
    const q=(x,y)=>{
      // A quarter turn preserves every body, eye and sear-mark dimension.
      // The larger drawing area prevents the original broad body being shortened.
      if(p.parallelPose)return [Math.round(boundary+(y-38)+(p.bodyX||0)),Math.round(48-(x-48)+(p.bodyY||0))];
      if(p.testPose){const a=p.tilt||0,dx=(x-48)*p.sx,dy=(y-32)*p.sy;return [Math.round(48+dx*Math.cos(a)-dy*Math.sin(a)+p.bodyX),Math.round(32+dx*Math.sin(a)+dy*Math.cos(a)+(p.bodyY||0))];}
      let xx=48+(x-48)*p.sx,yy=49+(y-49)*p.sy+p.dy;
      if(p.gripping){const a=p.tilt||0,dx=xx-56,dy=yy-42;xx=56+dx*Math.cos(a)-dy*Math.sin(a)+(p.bodyX||0);yy=42+dx*Math.sin(a)+dy*Math.cos(a);}
      return [Math.round(xx),Math.round(yy+(p.portraitPeek?0:16))];
    };
    // Occlude the lower body, without resizing the character or its eyes.
    const upperPart=pts=>{
      if(!p.upperOnly)return pts;
      const clipped=[];
      for(let i=0;i<pts.length;i++){
        const a=pts[i],b=pts[(i+1)%pts.length],insideA=a[1]<=38,insideB=b[1]<=38;
        if(insideA)clipped.push(a);
        if(insideA!==insideB)clipped.push([a[0]+(b[0]-a[0])*(38-a[1])/(b[1]-a[1]),38]);
      }
      return clipped;
    };
    const poly=(pts,c)=>{const visible=upperPart(pts);if(visible.length>=3)polygon(ctx,visible.map(([x,y])=>q(x,y)),c);};
    const rect=(x,y,w,h,c)=>poly([[x,y],[x+w,y],[x+w,y+h],[x,y+h]],c);
    const foot=(offset,d)=>{
      const path=pts=>ref(pts.map(([x,y])=>[x+offset,y+d*18]));
      poly(path([[468,726],[598,726],[598,745],[658,745],[658,758],[685,758],[685,806],[424,806],[424,758],[449,758],[449,745],[468,745]]),palette.outline);
      poly(path([[495,726],[598,726],[598,745],[658,745],[658,783],[449,783],[449,763],[472,763],[472,745],[495,745]]),palette.light);
    };
    if(!p.upperOnly&&(!p.gripping||p.showFeet)){foot(0,-Math.round(p.foot));foot(644,Math.round(p.foot));}
    const hand=right=>{
      const up=right?0:Math.round(p.wave*10),path=pts=>ref(pts.map(([x,y])=>[right?1750-x:x,y-up*18]));
      poly(path([[166,458],[216,458],[216,484],[242,484],[242,605],[216,605],[216,630],[193,630],[193,655],[142,655],[142,632],[116,632],[116,606],[90,606],[90,540],[116,540],[116,509],[142,509],[142,482],[166,482]]),palette.outline);
      poly(path([[168,484],[190,484],[190,553],[215,553],[215,606],[193,606],[193,629],[142,629],[142,605],[117,605],[117,542],[142,542],[142,508],[168,508]]),palette.light);
    };
    if(!p.gripping&&!p.upperOnly){hand(false);hand(true);}
    poly(shape,palette.outline);
    poly(ref([[620,155],[1131,155],[1131,182],[1209,182],[1209,208],[1283,208],[1283,232],[1340,232],[1340,258],[1383,258],[1383,283],[1429,283],[1429,307],[1455,307],[1455,333],[1481,333],[1481,370],[1507,370],[1507,417],[1532,417],[1532,549],[1507,549],[1507,596],[1478,596],[1478,620],[1445,620],[1445,643],[1405,643],[1405,665],[1343,665],[1343,699],[1152,699],[1152,723],[598,723],[598,700],[408,700],[408,677],[346,677],[346,653],[307,653],[307,630],[273,630],[273,605],[243,605],[243,549],[219,549],[219,417],[242,417],[242,370],[269,370],[269,333],[296,333],[296,307],[325,307],[325,282],[367,282],[367,257],[414,257],[414,232],[468,232],[468,207],[541,207],[541,181],[620,181]]),palette.rim);
    poly(ref([[620,155],[1131,155],[1131,182],[1209,182],[1209,208],[1283,208],[1283,232],[1340,232],[1340,258],[1383,258],[1383,283],[1429,283],[1429,307],[1455,307],[1455,333],[1481,333],[1481,370],[1507,370],[1507,417],[1532,417],[1532,523],[1507,523],[1507,549],[1479,549],[1479,573],[1444,573],[1444,597],[1407,597],[1407,619],[1343,619],[1343,642],[1243,642],[1243,662],[1119,662],[1119,682],[632,682],[632,662],[508,662],[508,642],[409,642],[409,619],[346,619],[346,597],[307,597],[307,573],[273,573],[273,549],[243,549],[243,523],[219,523],[219,417],[242,417],[242,370],[269,370],[269,333],[296,333],[296,307],[325,307],[325,282],[367,282],[367,257],[414,257],[414,232],[468,232],[468,207],[541,207],[541,181],[620,181]]),palette.red);
    // The two original diagonal sear marks remain attached to the same body.
    poly(ref([[504,262],[542,262],[542,310],[518,310],[518,334],[494,334],[494,358],[471,358],[471,382],[448,382],[448,405],[425,405],[425,427],[402,427],[402,449],[382,449],[382,471],[359,471],[359,494],[320,494],[320,447],[342,447],[342,426],[363,426],[363,404],[386,404],[386,382],[408,382],[408,358],[431,358],[431,334],[455,334],[455,310],[478,310],[478,286],[504,286]]),palette.rim);
    poly(ref([[1355,331],[1395,331],[1395,377],[1373,377],[1373,400],[1351,400],[1351,423],[1329,423],[1329,445],[1306,445],[1306,467],[1284,467],[1284,489],[1262,489],[1262,512],[1239,512],[1239,535],[1217,535],[1217,558],[1178,558],[1178,513],[1200,513],[1200,490],[1222,490],[1222,467],[1244,467],[1244,445],[1266,445],[1266,423],[1288,423],[1288,400],[1310,400],[1310,377],[1333,377],[1333,354],[1355,354]]),palette.rim);
    function eye(x) {
      // Lift the whole original eye, including its pupil and lid; never reshape it.
      x+=p.parallelPose?Math.round(p.eyeLift||0):0;
      poly([[x+3,23],[x+10,23],[x+10,25],[x+13,25],[x+13,28],[x+14,28],[x+14,34],[x+12,34],[x+12,37],[x+9,37],[x+9,38],[x+3,38],[x+3,36],[x,36],[x,26],[x+3,26]],palette.eye);
      const px=x+6+Math.round(p.upperOnly&&!p.animateEyes?0:p.lookX), py=29+Math.round(p.upperOnly&&!p.animateEyes?0:p.lookY);
      rect(px,py,4,5,palette.outline);rect(px-1,py+1,6,3,palette.outline);
      if(p.lid>0&&(!p.upperOnly||p.animateEyes)) {
        const h=Math.round(clamp(p.lid)*16);rect(x-1,22,16,h,palette.red);
        if(p.lid>.65) rect(x+1,Math.min(36,22+h),11,1,palette.outline);
      }
    }
    eye(32);eye(49);
    if(!p.upperOnly){
    if(p.mouth==='happy'){rect(44,39,9,3,palette.outline);rect(46,42,5,1,palette.outline);}
    else if(p.mouth==='sleep')rect(46,40,4,2,palette.outline);
    else poly(ref([[791,569],[818,569],[818,592],[843,592],[843,602],[909,602],[909,592],[935,592],[935,569],[961,569],[961,597],[935,597],[935,628],[818,628],[818,597],[791,597]]),palette.outline);
    }
    if(p.noteOpen&&p.parallelPose){
      const h=Math.max(1,Math.round(6*(p.noteAmount??1))),top=68-Math.floor(h/2);
      ctx.fillStyle=palette.rim;ctx.fillRect(boundary-10,top-1,10,h+2);
      ctx.fillStyle=palette.outline;ctx.fillRect(boundary-8,top,8,h);
    }
    ctx.restore();ctx.save(); // Hands overlap the screen lip; only the body is occluded.
    if(p.gripping){
      // Mitten hands stay in viewport coordinates; body transform never moves the contact.
      const gripHand=(y,amount,upper=false)=>{
        if(!amount)return;
        const x=boundary+Math.round((1-amount)*13);
        const shoulder=p.parallelPose?[x+2,y+3]:q(upper?62:49,upper?25:42);
        const elbow=[x-(p.parallelPose?4:13),y+5];
        polygon(ctx,[[shoulder[0]-2,shoulder[1]-2],[shoulder[0]+2,shoulder[1]+2],[elbow[0],elbow[1]+3],[x-3,y+6],[x-3,y],[elbow[0],elbow[1]-3]],palette.outline);
        polygon(ctx,[[shoulder[0],shoulder[1]],[elbow[0],elbow[1]+1],[x-4,y+4],[x-4,y+2],[elbow[0],elbow[1]-1]],palette.red);
        // One soft mitten silhouette, with no finger lines or separate digits.
        const mitten=(points,color)=>polygon(ctx,points.map(([dx,dy])=>[x+dx,y+dy]),color);
        mitten([[-7,-2],[-2,-2],[-2,-1],[1,-1],[1,1],[3,1],[3,8],[1,8],[1,11],[-2,11],[-2,12],[-7,12],[-7,10],[-10,10],[-10,7],[-12,7],[-12,3],[-10,3],[-10,0],[-7,0]],palette.outline);
        mitten([[-7,0],[-2,0],[-2,1],[1,1],[1,8],[-1,8],[-1,10],[-7,10],[-7,8],[-9,8],[-9,6],[-10,6],[-10,4],[-8,4],[-8,2],[-7,2]],palette.red);
        mitten([[-6,1],[-2,1],[-2,2],[0,2],[0,5],[-7,5],[-7,3],[-6,3]],palette.light);
      };
      gripHand(p.handY||(43+16),p.grip,(p.handY||43)<30);gripHand(p.hand2Y||33,p.grip2,true);
    }
    if(p.portraitPeek){
      ctx.fillStyle='#ded4c6';ctx.fillRect(0,38,W,1);
      for(const x of [24,74]){
        const mitten=(pts,c)=>polygon(ctx,pts.map(([dx,dy])=>[x+dx,38+dy]),c);
        mitten([[-5,-3],[4,-3],[4,-1],[6,-1],[6,5],[4,5],[4,7],[-4,7],[-4,5],[-6,5],[-6,-1],[-5,-1]],palette.outline);
        mitten([[-4,-1],[3,-1],[3,1],[4,1],[4,4],[2,4],[2,5],[-3,5],[-3,3],[-4,3]],palette.light);
      }
    }
    ctx.restore();
  }
  global.DenverSprite={width:W,height:H,palette,motions,sample,draw,clamp,ease,keys};
})(globalThis);
