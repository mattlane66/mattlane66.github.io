'use strict';
const TRACKS = JSON.parse(document.getElementById('trackData').textContent);
const audio = document.getElementById('audio');
const elements = Object.fromEntries(['play','playIcon','trackTitle','trackSub','trackNum','elapsed','total','seek','off','on','statusText','statusLed','tracks','count'].map(id=>[id,document.getElementById(id)]));
let selected = 0;
let lccEnabled = false;
let engine = null;
let enginePromise = null;
let lastError = null;
let scrubbing = false;

function fmt(s) {
  if (!Number.isFinite(s) || s < 0) return '0:00';
  const v = Math.floor(s);
  return `${Math.floor(v/60)}:${String(v%60).padStart(2,'0')}`;
}
function icon(isSelected) {
  return isSelected
    ? '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M5 4h5v16H5zm9 0h5v16h-5z"/></svg>'
    : '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
}
function refreshList() {
  elements.tracks.innerHTML = TRACKS.map((t,i)=>
    `<button role="listitem" type="button" class="track-button ${i===selected?'selected':''}" data-index="${i}" aria-current="${i===selected?'true':'false'}"><span class="track-icon">${icon(i===selected)}</span><span class="track-name">${t.title}</span><span class="track-length">${fmt(t.duration)}</span></button>`).join('');
}
function setStatus(text, error=false) {
  elements.statusText.textContent=text;
  elements.statusLed.className='led'+(error?' error':lccEnabled?' on':'');
}
function showMode() {
  elements.on.classList.toggle('active',lccEnabled);
  elements.off.classList.toggle('active',!lccEnabled);
  elements.on.setAttribute('aria-pressed',String(lccEnabled));
  elements.off.setAttribute('aria-pressed',String(!lccEnabled));
  if (engine?.worklet) engine.worklet.port.postMessage({type:'enable',value:lccEnabled});
  if (!lastError) setStatus(lccEnabled?'LCC processing on':'Original stereo · LCC off');
}
function setMode(value) {
  lccEnabled = Boolean(value);
  showMode();
}
function renderPlayback() {
  const playing=!audio.paused&&!audio.ended;
  elements.play.setAttribute('aria-label', playing?'Pause audio':'Play audio');
  elements.play.setAttribute('title', playing?'Pause':'Play');
  elements.playIcon.innerHTML = playing?'<path d="M6 4h4v16H6zm8 0h4v16h-4z"/>':'<path d="M7 4.5v15l13-7.5z"/>';
  const duration=Number.isFinite(audio.duration)?audio.duration:TRACKS[selected].duration;
  elements.total.textContent=fmt(duration);
  elements.elapsed.textContent=fmt(audio.currentTime);
  if(!scrubbing)elements.seek.value=duration>0?Math.floor(1000*audio.currentTime/duration):0;
}
function selectTrack(i) {
  if (i<0||i>=TRACKS.length) return;
  const wasPlaying=!audio.paused;
  audio.pause();
  selected=i;
  lastError=null;
  audio.src=TRACKS[i].src;
  audio.load();
  elements.trackTitle.textContent=TRACKS[i].title;
  elements.trackNum.textContent=`${String(i+1).padStart(2,'0')} / ${String(TRACKS.length).padStart(2,'0')}`;
  elements.trackSub.textContent=`Stereo · ${fmt(TRACKS[i].duration)}`;
  elements.total.textContent=fmt(TRACKS[i].duration);
  elements.elapsed.textContent='0:00';
  elements.seek.value=0;
  if(engine?.worklet)engine.worklet.port.postMessage({type:'reset'});
  refreshList();renderPlayback();showMode();
  if(wasPlaying)startPlayback();
}
async function initializeEngine() {
  const AudioCtor=window.AudioContext||window.webkitAudioContext;
  if(!AudioCtor||!window.AudioWorkletNode)throw new Error('This browser does not support AudioWorklet.');
  const context=new AudioCtor();
  if(!context.audioWorklet)throw new Error('This browser does not expose AudioWorklet.');
  await context.audioWorklet.addModule('lcc-worklet.js');
  const source=context.createMediaElementSource(audio);
  const worklet=new AudioWorkletNode(context,'lcc-processor',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[2]});
  source.connect(worklet);
  worklet.connect(context.destination);
  worklet.port.onmessage=(event)=>{
    if(event.data?.type==='error'){
      lastError=event.data.message||'Audio processing error';
      setStatus(lastError,true);
    }
  };
  worklet.port.postMessage({type:'enable',value:lccEnabled});
  engine={context,source,worklet};
  window.__lccTest={context,worklet,get mode(){return lccEnabled},get selected(){return TRACKS[selected].id}};
  return engine;
}
async function ensureEngine(){
  if(engine)return engine;
  if(!enginePromise)enginePromise=initializeEngine().catch(e=>{enginePromise=null;throw e;});
  return enginePromise;
}
async function startPlayback(){
  elements.play.disabled=true;
  lastError=null;
  try{
    setStatus('Preparing audio…');
    const e=await ensureEngine();
    await e.context.resume();
    if(e.context.state!=='running')throw new Error('Audio engine could not start. Tap Play again.');
    await audio.play();
    showMode();
  }catch(e){
    lastError=e?.message||'Cannot play this recording';
    setStatus(`Playback unavailable · ${lastError}`,true);
  }finally{
    elements.play.disabled=false;
    renderPlayback();
  }
}
function togglePlayback(){
  if(!audio.paused){audio.pause();renderPlayback();}
  else startPlayback();
}
elements.tracks.addEventListener('click',ev=>{
  const btn=ev.target.closest('button[data-index]');
  if(btn)selectTrack(Number(btn.dataset.index));
});
elements.play.addEventListener('click',togglePlayback);
elements.off.addEventListener('click',()=>setMode(false));
elements.on.addEventListener('click',()=>setMode(true));
elements.seek.addEventListener('input',()=>{
  scrubbing=true;
  const d=Number.isFinite(audio.duration)?audio.duration:TRACKS[selected].duration;
  elements.elapsed.textContent=fmt(Number(elements.seek.value)*d/1000);
});
elements.seek.addEventListener('change',()=>{
  const d=Number.isFinite(audio.duration)?audio.duration:TRACKS[selected].duration;
  if(d>0){audio.currentTime=Number(elements.seek.value)*d/1000;}
  scrubbing=false;
  if(engine?.worklet)engine.worklet.port.postMessage({type:'reset'});
  renderPlayback();
});
audio.addEventListener('timeupdate',renderPlayback);
audio.addEventListener('loadedmetadata',renderPlayback);
audio.addEventListener('playing',renderPlayback);
audio.addEventListener('pause',renderPlayback);
audio.addEventListener('ended',()=>{renderPlayback();showMode()});
audio.addEventListener('error',()=>{
  if(audio.error){lastError='The audio file could not be loaded';setStatus(lastError,true);}
});
elements.count.textContent=`${TRACKS.length} tracks`;
selectTrack(0);
// Preinitialize the worklet ahead of the first click when possible: Safari's
// first user gesture can then synchronously resume the already-wired graph.
if (window.isSecureContext || location.hostname==='localhost' || location.hostname==='127.0.0.1') {
  ensureEngine().catch(e=>{lastError=e.message;setStatus(`Audio engine unavailable · ${e.message}`,true);});
}
