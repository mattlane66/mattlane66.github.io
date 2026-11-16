'use strict';

// Each short lossless recording is decoded once into an AudioBuffer. A single
// AudioBufferSourceNode transports it at a known offset, avoiding the media
// element's asynchronous seek/play races (especially with FLAC).
const TRACKS = JSON.parse(document.getElementById('trackData').textContent);
const elements = Object.fromEntries([
  'play','playIcon','trackTitle','trackSub','trackNum','elapsed',
  'total','seek','off','on','statusText','statusLed','tracks','count'
].map(id=>[id,document.getElementById(id)]));

let selected = 0;
let lccEnabled = false;
let context = null;
let engine = null;
let enginePromise = null;
let playing = false;
let wantsPlayback = false;
let active = null;
let position = 0;
let revision = 0;
let scrubbing = false;
let lastError = null;
const buffers = new Map();

function fmt(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const s = Math.floor(seconds);
  return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
}
function trackDuration(i=selected) {
  const track=TRACKS[i];
  const buffer=buffers.get(track.id)?.value;
  return Math.max(0,(buffer?.duration ?? track.duration)-(track.cueIn||0));
}
function clampPosition(seconds) {
  return Math.max(0,Math.min(trackDuration(),Number.isFinite(seconds)?seconds:0));
}
function actualPosition() {
  if (!playing || !active || !context) return clampPosition(position);
  return clampPosition(active.position + Math.max(0,context.currentTime-active.started));
}
function render() {
  const isRunning=wantsPlayback;
  elements.play.setAttribute('aria-label',isRunning?'Pause audio':'Play audio');
  elements.play.setAttribute('title',isRunning?'Pause':'Play');
  elements.playIcon.innerHTML=isRunning
    ? '<path d="M6 4h4v16H6zm8 0h4v16h-4z"/>'
    : '<path d="M7 4.5v15l13-7.5z"/>';
  const duration=trackDuration();
  const t=actualPosition();
  elements.total.textContent=fmt(duration);
  if(!scrubbing){
    elements.elapsed.textContent=fmt(t);
    elements.seek.value=duration>0?String(Math.round(1000*t/duration)):'0';
  }
}
function setStatus(text,error=false){
  elements.statusText.textContent=text;
  elements.statusLed.className='led'+(error?' error':lccEnabled?' on':'');
}
function showMode(){
  elements.on.classList.toggle('active',lccEnabled);
  elements.off.classList.toggle('active',!lccEnabled);
  elements.on.setAttribute('aria-pressed',String(lccEnabled));
  elements.off.setAttribute('aria-pressed',String(!lccEnabled));
  if(engine)engine.worklet.port.postMessage({type:'enable',value:lccEnabled});
  if(!lastError)setStatus(lccEnabled?'LCC processing on':'Original stereo · LCC off');
}
function refreshList(){
  elements.tracks.innerHTML=TRACKS.map((t,i)=>
    `<div role="listitem"><button type="button" class="track-button ${i===selected?'selected':''}" data-index="${i}" aria-current="${i===selected?'true':'false'}"><span class="track-name">${t.title}</span><span class="track-length">${fmt(Math.max(0,t.duration-(t.cueIn||0)))}</span></button></div>`
  ).join('');
}

function stopActive(){
  const previous=active;
  active=null;
  playing=false;
  if(!previous||!context)return;
  const now=context.currentTime;
  try{
    previous.gain.gain.cancelScheduledValues(now);
    previous.gain.gain.setValueAtTime(previous.gain.gain.value,now);
    previous.gain.gain.linearRampToValueAtTime(0,now+0.006);
  }catch(_error){/* A stale gain envelope must not block stopping. */}
  try{previous.source.stop(now+0.009)}catch(_error){/* Already ended. */}
}
function startSource(buffer,logicalPosition){
  if(!engine)return;
  const remaining=trackDuration()-logicalPosition;
  if(remaining<=0){finishPlayback();return;}
  const now=context.currentTime;
  const source=context.createBufferSource();
  const gain=context.createGain();
  const at=now+0.002;
  gain.gain.setValueAtTime(0,at);
  gain.gain.linearRampToValueAtTime(1,at+0.006);
  source.buffer=buffer;
  source.connect(gain);
  gain.connect(engine.worklet);
  const cue=TRACKS[selected].cueIn||0;
  const startOffset=cue+logicalPosition;
  const item={source,gain,position:logicalPosition,started:at,selected};
  source.onended=()=>{
    source.disconnect();gain.disconnect();
    if(active!==item)return;
    active=null;
    playing=false;
    wantsPlayback=false;
    position=trackDuration();
    setStatus(lccEnabled?'LCC processing on':'Original stereo · LCC off');
    render();
  };
  active=item;
  playing=true;
  source.start(at,startOffset,remaining);
  render();
}
function finishPlayback(){
  wantsPlayback=false;
  position=trackDuration();
  stopActive();
  render();
}
async function ensureEngine(){
  if(engine)return engine;
  if(enginePromise)return enginePromise;
  const AudioCtor=window.AudioContext||window.webkitAudioContext;
  if(!AudioCtor||!window.AudioWorkletNode)throw new Error('AudioWorklet is not supported by this browser.');
  if(!context)context=new AudioCtor({latencyHint:'interactive'});
  enginePromise=(async()=>{
    await context.audioWorklet.addModule('lcc-worklet.js?v=5');
    const worklet=new AudioWorkletNode(context,'lcc-processor',{
      numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[2]
    });
    worklet.connect(context.destination);
    worklet.port.postMessage({type:'enable',value:lccEnabled});
    engine={worklet};
    return engine;
  })();
  enginePromise.catch(()=>{enginePromise=null;});
  return enginePromise;
}
function loadTrack(index){
  const track=TRACKS[index];
  if(buffers.has(track.id))return buffers.get(track.id).promise;
  const record={value:null,promise:null};
  record.promise=(async()=>{
    await ensureEngine();
    const response=await fetch(track.src);
    if(!response.ok)throw new Error(`${track.title} could not load (HTTP ${response.status}).`);
    const bytes=await response.arrayBuffer();
    const buffer=await context.decodeAudioData(bytes);
    if(buffer.numberOfChannels!==2)throw new Error(`${track.title} is not stereo.`);
    record.value=buffer;
    return buffer;
  })().catch(error=>{buffers.delete(track.id);throw error;});
  buffers.set(track.id,record);
  return record.promise;
}
async function startPlayback(){
  if(wantsPlayback&&playing)return;
  wantsPlayback=true;
  lastError=null;
  const token=++revision;
  if(position>=trackDuration()-.005)position=0;
  render();
  setStatus('Loading audio…');
  try{
    // Resume immediately within the click, before awaiting a fetch or decode.
    const preparing=ensureEngine();
    const resume=context?.resume();
    const bufferPromise=loadTrack(selected);
    await preparing;
    if(resume)await resume;
    const buffer=await bufferPromise;
    if(!wantsPlayback||revision!==token)return;
    if(context.state!=='running')await context.resume();
    if(!wantsPlayback||revision!==token)return;
    startSource(buffer,clampPosition(position));
    showMode();
  }catch(error){
    if(revision!==token)return;
    wantsPlayback=false;
    playing=false;
    lastError=error?.message||'Unable to play this recording';
    setStatus(`Playback unavailable · ${lastError}`,true);
    render();
  }
}
function pausePlayback(){
  if(!wantsPlayback)return;
  revision++;
  position=actualPosition();
  wantsPlayback=false;
  stopActive();
  if(!lastError)setStatus(lccEnabled?'LCC processing on':'Original stereo · LCC off');
  render();
}
function switchTrack(index){
  if(!Number.isInteger(index)||index<0||index>=TRACKS.length||index===selected)return;
  const resume=wantsPlayback;
  revision++;
  wantsPlayback=false;
  stopActive();
  selected=index;
  position=0;
  lastError=null;
  elements.trackTitle.textContent=TRACKS[selected].title;
  elements.trackSub.textContent=`Stereo · ${fmt(trackDuration())}`;
  elements.trackNum.textContent=`${String(selected+1).padStart(2,'0')} / ${String(TRACKS.length).padStart(2,'0')}`;
  refreshList();render();showMode();
  if(resume)void startPlayback();
  else void loadTrack(selected).catch(()=>{}); // predecode without autoplay
}
function seekTo(t){
  const next=clampPosition(t);
  // Input followed by change can describe the same slider position. Avoid
  // stopping and rebuilding the source twice for that single user action.
  if(Math.abs(next-actualPosition())<0.025){position=next;render();return;}
  position=next;
  if(playing&&active){
    const buffer=buffers.get(TRACKS[selected].id)?.value;
    stopActive();
    if(buffer){
      if(position<trackDuration()-.005)startSource(buffer,position);
      else finishPlayback();
    }
  }
  render();
}
function seekFromSlider(){
  const t=Number(elements.seek.value)/1000*trackDuration();
  elements.elapsed.textContent=fmt(t);
  seekTo(t);
}

// All audio sequencing is driven by a single explicit playback intent.
elements.play.addEventListener('click',()=>{
  if(wantsPlayback)pausePlayback();
  else void startPlayback();
});
elements.tracks.addEventListener('click',event=>{
  const button=event.target.closest('button[data-index]');
  if(button)switchTrack(Number(button.dataset.index));
});
elements.off.addEventListener('click',()=>{lccEnabled=false;showMode()});
elements.on.addEventListener('click',()=>{lccEnabled=true;showMode()});
elements.seek.addEventListener('pointerdown',()=>{scrubbing=true});
elements.seek.addEventListener('pointerup',()=>{scrubbing=false;render()});
elements.seek.addEventListener('pointercancel',()=>{scrubbing=false;render()});
elements.seek.addEventListener('input',seekFromSlider);
elements.seek.addEventListener('change',()=>{seekFromSlider();scrubbing=false;render()});
elements.count.textContent=`${TRACKS.length} tracks`;
elements.trackTitle.textContent=TRACKS[0].title;
elements.trackSub.textContent=`Stereo · ${fmt(trackDuration())}`;
refreshList();showMode();render();

// Preload the first short FLAC ahead of the initial Play click. No autoplay.
// A failure is shown only after Play is explicitly requested.
void loadTrack(0).catch(()=>{});
function updateClock(){
  if(playing&&!scrubbing)render();
  requestAnimationFrame(updateClock);
}
requestAnimationFrame(updateClock);
window.__lccTest={
  get context(){return context},get selected(){return TRACKS[selected].id},
  get mode(){return lccEnabled},get playing(){return playing},
  get wantsPlayback(){return wantsPlayback},get position(){return actualPosition()},
  get loading(){return wantsPlayback&&!playing},
  get bufferReady(){return Boolean(buffers.get(TRACKS[selected].id)?.value)}
};
