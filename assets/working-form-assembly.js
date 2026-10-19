/* Pixel-faithful diagram construction, fixed 1.5×. Static original is the accessible fallback. */
(() => {
  const mount=document.querySelector('.hero-map[data-assemble="working-form"]');
  const fallback=mount&&mount.querySelector('img');
  if(!mount||!fallback||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  // [x,y,width,height,begin,end,isFrame]; begin/end are original animation units.
  const pieces=[
    [174,106,95,28,0,.18,0],[44,144,333,827,.08,.42,1],[77,153,249,174,.2,.36,1],[83,160,150,18,.24,.38,0],[83,179,105,42,.3,.46,0],[194,177,120,72,.38,.58,0],[82,248,232,18,.5,.66,0],[84,267,230,22,.6,.78,0],[84,288,230,28,.7,.9,0],
    [77,349,249,188,.88,1.04,1],[84,357,160,18,.92,1.1,0],[84,377,108,40,1,1.16,0],[196,373,120,76,1.08,1.28,0],[84,454,232,18,1.2,1.36,0],[84,474,232,54,1.3,1.56,0],
    [90,560,253,181,1.5,1.66,1],[98,568,150,18,1.54,1.72,0],[96,588,110,45,1.62,1.8,0],[209,582,121,76,1.7,1.9,0],[125,655,165,54,1.84,2.06,0],
    [77,772,270,190,1.98,2.14,1],[85,780,164,18,2.02,2.18,0],[84,800,109,42,2.1,2.28,0],[197,796,120,76,2.18,2.38,0],[84,877,245,18,2.28,2.44,0],[84,897,245,55,2.38,2.64,0],
    [811,0,101,22,2.55,2.7,0],[495,20,617,211,2.62,2.96,1],[510,20,85,85,2.78,2.94,1],[514,25,77,74,2.84,3.06,0],[622,48,93,156,2.96,3.16,1],[627,53,84,64,3.02,3.2,0],[628,118,83,49,3.12,3.32,0],[636,170,67,24,3.24,3.42,0],
    [733,86,88,96,3.24,3.42,1],[738,92,79,82,3.3,3.5,0],[845,66,89,120,3.46,3.66,1],[850,72,80,53,3.52,3.72,0],[850,126,80,53,3.64,3.86,0],[950,70,90,89,3.7,3.88,1],[955,76,80,78,3.76,3.98,0],[1051,125,130,81,3.92,4.12,1],[1056,131,120,70,3.98,4.2,0],
    [648,279,140,28,4.25,4.4,0],[526,313,355,68,4.3,4.52,1],[537,319,72,55,4.38,4.58,0],[609,327,64,40,4.48,4.68,0],[672,323,56,46,4.58,4.76,0],[728,327,56,40,4.66,4.84,0],[785,323,46,46,4.74,4.92,0],[831,327,43,40,4.84,5.04,0],
    [956,267,235,30,5.1,5.24,0],[913,299,285,109,5.14,5.36,1],[921,326,74,60,5.22,5.42,0],[995,322,96,66,5.34,5.56,0],[1091,319,69,28,5.48,5.66,0],[1088,348,101,45,5.58,5.8,0],
    [673,606,124,30,5.95,6.1,0],[566,643,310,285,6,6.24,1],[641,647,142,18,6.08,6.22,0],[611,647,171,113,6.12,6.32,1],[618,653,156,24,6.18,6.36,0],[621,680,150,20,6.28,6.44,0],[622,704,148,39,6.38,6.56,0],[623,743,145,12,6.5,6.7,0],[783,691,90,97,6.46,6.72,0],[608,767,153,18,6.62,6.78,0],[581,765,179,158,6.68,6.88,1],[589,771,164,24,6.74,6.92,0],[589,799,164,19,6.84,7,0],[590,822,162,32,6.94,7.14,0],[590,854,162,32,7.06,7.24,0],[592,889,158,26,7.18,7.36,0],
    [1351,196,104,36,7.45,7.6,0],[1241,228,284,515,7.52,7.78,1],[1283,244,208,166,7.64,7.82,1],[1288,249,199,26,7.7,7.88,0],[1289,276,197,28,7.8,7.98,0],[1289,306,198,67,7.94,8.16,0],[1290,374,196,28,8.08,8.26,0],[1282,409,208,155,8.18,8.36,1],[1287,414,199,26,8.24,8.42,0],[1289,441,197,28,8.34,8.52,0],[1289,470,198,57,8.46,8.68,0],[1290,528,196,28,8.6,8.78,0],[1290,574,206,161,8.7,8.88,1],[1295,579,198,26,8.76,8.94,0],[1296,606,197,28,8.86,9.04,0],[1296,635,198,63,8.98,9.2,0],[1296,699,196,28,9.12,9.3,0]
  ];
  // Each route follows an actual connector in the original diagram.
  // Never trace enclosing section borders as though they were wires.
  // Coordinate adjustments were checked against the source diagram.
  // Measured straight connector segments from the original image (x1,y1,x2,y2).
  // The actual image supplies the ink; these coordinates only advance the mask.
  const wireSegments=[[396,67,501,67],[469,177,502,177],[1216,178,1275,178],[381,191,470,191],[381,259,415,259],[440,259,506,259],[405,269,469,269],[400,438,440,438],[505,497,1256,497],[614,579,1103,579],[1112,579,1256,579],[1076,660,1256,660],[468,706,574,706],[456,716,574,716],[888,719,1077,719],[461,732,574,732],[439,835,574,835],[464,854,574,854],[381,863,447,863],[381,891,462,891],[1512,0,1512,231],[1538,0,1538,231],[1556,0,1556,615],[395,68,395,181],[1274,178,1274,231],[398,212,398,251],[505,259,505,498],[468,269,468,707],[1225,360,1225,450],[439,438,439,836],[456,465,456,717],[614,579,614,650],[1076,660,1076,719],[461,732,461,853],[461,854,461,891]];
  const NS='http://www.w3.org/2000/svg';
  const add=(tag,attrs,parent)=>{
    const el=document.createElementNS(NS,tag);
    for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));
    parent.appendChild(el);
    return el;
  };
  const svg=add('svg',{
    viewBox:'0 0 1568 1003',preserveAspectRatio:'xMidYMid meet',
    class:'hero-assembly','aria-hidden':'true',focusable:'false'
  },document.createDocumentFragment());
  add('rect',{x:0,y:0,width:1568,height:1003,fill:'#f8f9fb'},svg);
  const defs=add('defs',{},svg);
  add('image',{id:'hero-assembly-source',href:fallback.currentSrc||fallback.src,
    x:0,y:0,width:1568,height:1003},defs);
  const image=mask=>{
    add('use',{href:'#hero-assembly-source',mask:'url(#'+mask+')'},svg);
  };
  const makeMask=id=>add('mask',{
    id,maskUnits:'userSpaceOnUse',maskContentUnits:'userSpaceOnUse',
    x:0,y:0,width:1568,height:1003,'mask-type':'alpha'
  },defs);
  const clamp=x=>Math.max(0,Math.min(1,x));
  const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
  const fixedTime=(time)=>time*.68;

  // One original-image draw per layer. Individual elements animate through
  // the SVG mask, rather than creating 100+ duplicate bitmap draws.
  const frameMask=makeMask('hero-frame-mask');
  const pieceMask=makeMask('hero-piece-mask');
  const wireMask=makeMask('hero-wire-mask');
  const exactFinishMask=makeMask('hero-exact-finish-mask');
  image('hero-frame-mask');
  image('hero-piece-mask');
  image('hero-wire-mask');
  image('hero-exact-finish-mask');

  const frameStrokes=[],parts=[];
  for(const [x,y,width,height,from,to,isFrame] of pieces){
    if(isFrame){
      const stroke=add('rect',{x,y,width,height,fill:'none',stroke:'#fff',
        'stroke-width':5,opacity:1},frameMask);
      const length=2*(width+height);
      stroke.style.strokeDasharray=String(length);
      stroke.style.strokeDashoffset=String(length);
      frameStrokes.push({stroke,length,start:fixedTime(from),end:fixedTime(to)});
    }else{
      const rect=add('rect',{x,y,width,height,fill:'#fff',opacity:0},pieceMask);
      parts.push({rect,start:fixedTime(from),end:fixedTime(to)});
    }
  }

  // Strokes are measured against the real diagram, and reveal its existing
  // pixels with a narrow moving alpha mask (never a substitute blue line).
  const wires=wireSegments.map(([x1,y1,x2,y2],index)=>{
    const dx=x2-x1,dy=y2-y1,length=Math.abs(dx)+Math.abs(dy);
    const stroke=add('path',{d:'M '+x1+' '+y1+' L '+x2+' '+y2,
      fill:'none',stroke:'#fff','stroke-width':5,
      'stroke-linejoin':'miter','stroke-linecap':'square'},wireMask);
    stroke.style.strokeDasharray=String(length);
    stroke.style.strokeDashoffset=String(length);
    const mx=(x1+x2)/2,my=(y1+y2)/2;
    let start;
    if(mx>1500)start=5.95;
    else if(mx>1215 && my<260)start=5.65;
    else if(my<232)start=2.05;
    else if(my<420 && mx<530)start=3.05;
    else if(my<420 && mx>=900)start=4.15;
    else if(my<420)start=3.55;
    else if(my<550 && length>500)start=5.16;
    else if(my<550 && mx<530)start=4.10;
    else if(my<550)start=5.04;
    else if(my<785)start=4.66;
    else start=5.10;
    start+=(index%3)*.06;
    const end=start+Math.max(.18,Math.min(.70,length/1150));
    return {stroke,length,start,end};
  });

  // Complete each part of the image locally, soon after it has been built.
  // The rectangles partition 100% of the original's 1568×1003 pixels:
  // there is NO final full-image fade or focus switch. Each rectangle
  // contains exact original pixels, including authentic section shading.
  const completionTiles=[
    [0,0,380,1003,1.84],        // Finished Table (gray arrives after its UI)
    [380,0,122,233,3.00],       // Left goal connectors
    [502,0,713,233,3.00],       // Finished Set Goal
    [1215,0,353,233,5.68],      // Upper history routing and title
    [380,233,122,317,3.80],     // Table -> achievement
    [502,233,398,177,3.78],     // Finished Log Achievement
    [502,410,398,140,5.73],     // Achievement/history long routing
    [900,233,315,177,4.23],     // Finished Notify Coach
    [900,410,315,140,5.77],     // Coach/history wiring
    [1215,233,353,317,6.46],   // History gray only after the group is built
    [380,550,122,453,5.42],    // Table -> Add Maxes lower routing
    [502,550,398,453,5.42],    // Finished Add Maxes (actual gray pixels)
    [900,550,315,453,5.84],    // Maxes -> pool history
    [1215,550,353,453,6.46]   // Finished History
  ].map(([x,y,width,height,start])=>({
    rect:add('rect',{x,y,width,height,fill:'#fff',opacity:0},exactFinishMask),
    start
  }));
  let position=0,previous=null,visible=true;
  const duration=8.8,speed=1.5; // 5.9-second loop; user-selected fixed pace
  function draw(){
    for(const part of parts){
      part.rect.style.opacity=String(clamp((position-part.start)/(part.end-part.start)*5));
    }
    for(const frame of frameStrokes){
      const progress=smooth((position-frame.start)/(frame.end-frame.start));
      frame.stroke.style.strokeDashoffset=String(frame.length*(1-progress));
    }
    for(const wire of wires){
      const progress=clamp((position-wire.start)/(wire.end-wire.start));
      wire.stroke.style.strokeDashoffset=String(wire.length*(1-progress));
    }
    for(const tile of completionTiles){
      const p=smooth((position-tile.start)/.16);
      tile.rect.style.opacity=String(p);
    }
  }
  function tick(now){
    if(previous!==null&&visible&&!document.hidden){
      position=(position+Math.min(80,now-previous)/1000*speed)%duration;
      draw();
    }
    previous=now;requestAnimationFrame(tick);
  }
  function start(){
    mount.appendChild(svg);
    mount.classList.add('is-assembling');
    draw();
    if('IntersectionObserver' in window){
      new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;previous=null;},{threshold:.01}).observe(mount);
    }
    requestAnimationFrame(tick);
  }
  const ready=()=>fallback.decode?fallback.decode().then(start).catch(()=>{}):start();
  if(fallback.complete&&fallback.naturalWidth)ready();
  else fallback.addEventListener('load',ready,{once:true});
})();
