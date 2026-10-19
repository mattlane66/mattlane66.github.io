/* Assemble the homepage diagram at a fixed 2× rate. Image remains the fallback. */
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
  const wires=[
    ['M 319 182 H 391 V 67 H 511',2.32,2.96],['M 319 181 H 620',2.46,3.1],['M 499 20 V 229 H 1112',3.95,4.55],
    ['M 321 253 H 499 V 315 H 526',4.2,4.82],['M 375 262 H 464 V 490 H 499',4.36,4.98],['M 878 345 H 918',5,5.22],
    ['M 1186 356 H 1211 V 444 H 1282',5.7,6.1],['M 322 434 H 434 V 708 H 611',6.2,6.7],['M 322 461 H 453 V 729 H 612',6.34,6.84],
    ['M 339 853 H 441 V 826 H 583',6.58,7.02],['M 342 880 H 455 V 724 H 583',6.72,7.2],
    ['M 1113 162 H 1130 V 176 H 1139 M 1180 177 H 1260 V 280 H 1284',7.62,8.16],
    ['M 499 380 V 492 H 1285',7.86,8.42],['M 876 711 H 1065 V 654 H 1289',8.06,8.56],
    ['M 607 644 V 572 H 1279',8.22,8.72],['M 1494 232 V 22 H 1520 V 607 H 1492',8.42,8.96],
    ['M 1242 228 H 1521 V 742 H 1242 V 228',8.58,9.12]
  ];
  const NS='http://www.w3.org/2000/svg';
  const add=(tag,attrs,parent)=>{
    const el=document.createElementNS(NS,tag);
    Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));
    parent.appendChild(el);return el;
  };
  const svg=document.createElementNS(NS,'svg');
  Object.entries({viewBox:'0 0 1568 1003',preserveAspectRatio:'xMidYMid meet',class:'hero-assembly','aria-hidden':'true',focusable:'false'})
    .forEach(([k,v])=>svg.setAttribute(k,v));
  // Keep the underlying paper steady, but finish each section with its own
  // gray wash after its fields, boxes, and labels have been assembled.
  // The fills are behind the assembled details (not painted over them).
  add('rect',{x:0,y:0,width:1568,height:1003,fill:'#f8f9fb'},svg);
  const sectionBackgrounds=[
    [44,144,333,827,2.64],   // Table completes
    [495,20,617,211,4.20],   // Set Goal completes
    [566,643,310,285,7.36], // Add Maxes completes
    [1241,228,284,515,9.30] // History completes
  ].map(([x,y,width,height,after])=>({
    el:add('rect',{x,y,width,height,fill:'#e5e9ed',opacity:0},svg),
    after:after*.68
  }));
  const defs=add('defs',{},svg);
  add('image',{id:'hero-assembly-source',href:fallback.currentSrc||fallback.src,x:0,y:0,width:1568,height:1003},defs);
  // Show exact bitmap pixels as elements assemble. Traced paths are used only
  // as alpha masks; no temporary colored lines or softened substitutes.
  const frames=add('g',{},svg), sections=add('g',{},svg);
  const cables=add('g',{},svg), completed=add('g',{},svg);
  const original=add('use',{href:'#hero-assembly-source',opacity:0},svg);
  const clamp=v=>Math.max(0,Math.min(1,v));
  const cubic=v=>1-Math.pow(1-clamp(v),3);
  const snap=v=>{v=clamp(v);return v<.76?1-Math.pow(1-v/.76,5):1};
  const bitmapClip=(id,x,y,width,height,parent)=>{
    const clip=add('clipPath',{id,clipPathUnits:'userSpaceOnUse'},defs);
    add('rect',{x,y,width,height},clip);
    const el=add('g',{'clip-path':'url(#'+id+')',opacity:0},parent);
    add('use',{href:'#hero-assembly-source'},el);
    return el;
  };
  // Mask geometry is intentionally non-rendered in browsers; querying
  // SVGGeometryElement.getTotalLength() there throws in Chromium and Safari.
  // All routes here are absolute orthogonal M/H/V moves, so measure directly.
  const routeLength=d=>{
    const tokens=d.match(/[MHV]|-?[0-9]+(?:[.][0-9]+)?/g)||[];
    let x=0,y=0,distance=0;
    for(let i=0;i<tokens.length;){
      const cmd=tokens[i++];
      if(cmd==='M'){
        x=Number(tokens[i++]); y=Number(tokens[i++]);
      }else if(cmd==='H'){
        const nx=Number(tokens[i++]);distance+=Math.abs(nx-x);x=nx;
      }else if(cmd==='V'){
        const ny=Number(tokens[i++]);distance+=Math.abs(ny-y);y=ny;
      }else throw Error('Unsupported wire path instruction');
    }
    return distance;
  };
  const bitmapStroke=(id,tag,attributes,parent)=>{
    const mask=add('mask',{
      id,maskUnits:'userSpaceOnUse',maskContentUnits:'userSpaceOnUse',
      x:0,y:0,width:1568,height:1003,'mask-type':'alpha'
    },defs);
    const trace=add(tag,{...attributes,fill:'none',stroke:'#fff','stroke-width':8},mask);
    add('use',{href:'#hero-assembly-source',mask:'url(#'+id+')'},parent);
    const length=tag==='rect'
      ? 2*(Number(attributes.width)+Number(attributes.height))
      : routeLength(attributes.d);
    trace.style.strokeDasharray=String(length);
    trace.style.strokeDashoffset=String(length);
    return {trace,length};
  };
  const fragments=pieces.map(([x,y,w,h,start,end,frame],i)=>{
    start*=.68;end*=.68;
    if(frame){
      const {trace,length}=bitmapStroke('hero-frame-mask-'+i,'rect',
        {x,y,width:w,height:h},frames);
      return {trace,length,start,end,frame:true};
    }
    return {
      el:bitmapClip('hero-assembly-clip-'+i,x,y,w,h,sections),
      start,end,frame:false
    };
  });
  const paths=wires.map(([d,start,end],i)=>{
    const {trace,length}=bitmapStroke('hero-wire-mask-'+i,'path',
      {d,'stroke-linecap':'square','stroke-linejoin':'miter'},cables);
    return {trace,length,start:start*.68,end:end*.68};
  });
  // Once a section is finished, show the complete original pixels in its
  // region. Its gray fill appears independently a moment beforehand. This
  // prevents an abrupt jump from low-contrast construction to sharp raster.
  const finishedSections=[
    [44,144,333,827,2.64],     // Table
    [495,20,617,211,4.20],     // Set Goal
    [526,313,355,68,5.04],     // Log Achievement
    [913,299,285,109,5.80],    // Notify Coach
    [566,643,310,285,7.36],   // Add Maxes
    [1241,228,284,515,9.30]   // History
  ].map(([x,y,w,h,after],i)=>({
    el:bitmapClip('hero-complete-clip-'+i,x,y,w,h,completed),
    after:after*.68+(i===2||i===3?.05:.24)
  }));
  let position=0,previous=null,visible=true;
  const duration=8.8,speed=1.5; // fixed pace: approximately 5.9 seconds per loop
  function draw(){
    // A section's gray background arrives only after its elements are placed.
    for(const bg of sectionBackgrounds){
      const progress=clamp((position-bg.after)/.24);
      bg.el.style.opacity=String(progress*progress*(3-2*progress));
    }
    for(const o of fragments){
      const progress=(position-o.start)/(o.end-o.start);
      if(o.frame){
        // Reveal the frame's *actual* pixels along its perimeter.
        o.trace.style.strokeDashoffset=String(o.length*(1-snap(progress)));
      }else{
        // Pixels are full-contrast as soon as a module snaps into place.
        o.el.style.opacity=String(clamp(progress*5));
      }
    }
    for(const wire of paths){
      wire.trace.style.strokeDashoffset=String(wire.length*(1-cubic(
        (position-wire.start)/(wire.end-wire.start))));
    }
    for(const section of finishedSections){
      const p=clamp((position-section.after)/.16);
      section.el.style.opacity=String(p*p*(3-2*p));
    }
    // Resolve the few pixels outside the explicit construction paths after
    // the last section has finished; nothing changes sharpness at loop's end.
    const finish=clamp((position-6.65)/.3);
    original.style.opacity=String(finish*finish*(3-2*finish));
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
