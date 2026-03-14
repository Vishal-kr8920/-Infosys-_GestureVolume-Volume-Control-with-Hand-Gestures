const volumeCtx=document.getElementById("volumeChart");
const distanceCtx=document.getElementById("distanceChart");

let volumeChart=new Chart(volumeCtx,{
type:'line',
data:{
labels:Array.from({length:40},(_,i)=>i),
datasets:[{
label:'Volume (%)',
data:[],
borderColor:'green',
fill:false
}]
},
options:{
animation:false,
scales:{
x:{
title:{display:true,text:"Time (frames)"},
min:0,
max:39
},
y:{
title:{display:true,text:"Volume (%)"},
min:0,
max:100
}
}
}
});

let distanceChart=new Chart(distanceCtx,{
type:'line',
data:{
labels:Array.from({length:40},(_,i)=>i),
datasets:[{
label:'Distance (mm)',
data:[],
borderColor:'blue',
fill:false
}]
},
options:{
animation:false,
scales:{
x:{
title:{display:true,text:"Time (frames)"},
min:0,
max:39
},
y:{
title:{display:true,text:"Distance (mm)"},
min:0,
max:200
}
}
}
});

function update(){

fetch('/metrics')

.then(res=>res.json())

.then(data=>{

document.getElementById("volume").innerText=data.volume+"%";
document.getElementById("distance").innerText=data.distance;
document.getElementById("fps").innerText=data.fps;
document.getElementById("hands").innerText=data.hands;
document.getElementById("gesture").innerText=data.gesture;
document.getElementById("gesture_recognition").innerText=data.gesture_recognition;

volumeChart.data.datasets[0].data=data.volume_history;
volumeChart.update();

distanceChart.data.datasets[0].data=data.distance_history;
distanceChart.update();

})

}

setInterval(update,100)

function startCamera(){fetch('/start_camera')}
function pauseCamera(){fetch('/stop_camera')}
