/* Small numerical and lifecycle contracts, shared by both experiences. */
(function(root,f){if(typeof module==='object'&&module.exports)module.exports=f();else root.LoomCore=f();})(typeof globalThis==='object'?globalThis:this,function(){'use strict';
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function zoomPath(distance,w0,w1){
 if(![distance,w0,w1].every(Number.isFinite)||distance<0||w0<=0||w1<=0)throw new RangeError('Finite positive camera widths required');
 const rho=Math.SQRT2;
 if(distance<1e-7*Math.max(w0,w1))return {S:Math.abs(Math.log(w1/w0))/rho,at:t=>({f:clamp(t,0,1),w:w0*Math.exp(Math.log(w1/w0)*clamp(t,0,1))})};
 const b0=(w1*w1-w0*w0+4*distance*distance)/(4*w0*distance),b1=(w1*w1-w0*w0-4*distance*distance)/(4*w1*distance);
 // -asinh(b) is algebraically identical to log(sqrt(1+b*b)-b), without cancellation.
 const r0=-Math.asinh(b0),r1=-Math.asinh(b1),S=(r1-r0)/rho;
 return {S,at:t=>{if(t<=0)return {f:0,w:w0};if(t>=1)return {f:1,w:w1};const s=t*S*rho,den=Math.cosh(r0+s);return {f:clamp(w0*.5*Math.sinh(s)/den/distance,0,1),w:w0*Math.cosh(r0)/den};}};
}
const focal=(w,h,fov)=>Math.min(w,h)*.5/Math.tan(fov*.5);
function profileVerdict(report,reasons,elapsed){const failures=[...new Set(reasons)];if(report.draw_intervals.samples<120)failures.push('fewer than 120 draw intervals');if(elapsed<5000)failures.push('less than 5 seconds');if(report.gpu.disjoint_events)failures.push('GPU disjoint event');return {valid:!failures.length,reasons:failures};}
function acceptedMessage(e,source,origin,session,types){const d=e.data;return !!(e.source===source&&e.origin===origin&&d&&d.protocol==='loom-observatory/1'&&d.session===session&&types.includes(d.type));}
function chooseJoin(canonical,rows){const matches=rows.filter(n=>n.cls==='NodeType'&&n.id===canonical.toLowerCase()&&n.label.toLowerCase()===canonical.toLowerCase());return matches.length===1?matches[0]:null;}
function poseError(a,b){if(!Array.isArray(a)||!Array.isArray(b)||a.length!==3||b.length!==3||![...a,...b].every(Number.isFinite))return null;return Math.hypot(...a.map((x,i)=>x-b[i]));}
function appliedForIntent(applied,intent){return !!(applied&&intent&&Number.isInteger(intent.serial)&&Number.isInteger(intent.requestedFrame)&&Number.isInteger(applied.frame)&&applied.serial===intent.serial&&applied.frame>intent.requestedFrame&&applied.complete===true);}
return {appliedForIntent,clamp,zoomPath,focal,profileVerdict,acceptedMessage,chooseJoin,poseError};
});
