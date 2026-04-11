console.log("Sistema carregado");

// ================= CHAT =================
async function send(){
 let msg=document.getElementById("msg").value;
 if(!msg) return;

 appendMessage(msg,"user");

 let res=await fetch("/api/chat",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({message:msg})
 });

 let data=await res.json();
 appendMessage(data.response,"bot");

 document.getElementById("msg").value="";
}

function appendMessage(text,type){
 let div=document.createElement("div");
 div.classList.add("msg",type);
 div.innerText=text;
 document.getElementById("chat-history").appendChild(div);
}

function clearChat(){
 document.getElementById("chat-history").innerHTML="";
}

function toggleDNA(){
 document.getElementById("dna-panel").classList.toggle("hidden");
}

// ================= DNA =================
async function gc(){
 let seq=document.getElementById("dna-seq").value;
 let res=await fetch("/api/dna/gc",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sequence:seq})});
 let data=await res.json();
 document.getElementById("dna-result").innerText="GC: "+data.gc+"%";
}

async function toRNA(){
 let seq=document.getElementById("dna-seq").value;
 let res=await fetch("/api/dna/to_rna",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sequence:seq})});
 let data=await res.json();
 document.getElementById("dna-result").innerText="RNA: "+data.rna;
}

// ================= PROTEÍNA =================
let stage;

function initProteinViewer(){
 stage=new NGL.Stage("protein-viewer");
}

function renderProtein(){
 stage.removeAllComponents();
 stage.loadFile("rcsb://1CRN").then(o=>{
   o.addRepresentation("cartoon");
   o.autoView();
 });
}

// ================= TRANSLATE =================
async function translate(){
 let seq=document.getElementById("dna-seq").value;

 let res=await fetch("/api/rna/translate",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({sequence:seq})
 });

 let data=await res.json();

 if(data.error){
   document.getElementById("dna-result").innerText="Erro: "+data.error;
   return;
 }

 document.getElementById("dna-result").innerText="Proteína: "+data.protein;

 renderProtein();
}

// ================= DNA 3D =================
function renderDNA(){

 let seq=document.getElementById("dna-seq").value.toUpperCase();
 if(!seq) return;

 let viewer=document.getElementById("viewer");
 viewer.innerHTML="";

 let scene=new THREE.Scene();
 let camera=new THREE.PerspectiveCamera(75,viewer.clientWidth/300,0.1,1000);
 let renderer=new THREE.WebGLRenderer({antialias:true});

 renderer.setSize(viewer.clientWidth,300);
 viewer.appendChild(renderer.domElement);

 camera.position.z=60;

 let light=new THREE.PointLight(0xffffff,1);
 light.position.set(50,50,50);
 scene.add(light);

 function cor(b){return {A:0xff4d4d,T:0x4dff4d,C:0x4d4dff,G:0xffff4d}[b]||0xffffff;}
 function comp(b){return {A:"T",T:"A",C:"G",G:"C"}[b]||"N";}

 let angle=0, r=10, step=2;

 for(let i=0;i<seq.length;i++){
   let b1=seq[i];
   let b2=comp(b1);

   let x1=Math.cos(angle)*r;
   let y1=Math.sin(angle)*r;
   let z=i*step;

   let x2=Math.cos(angle+Math.PI)*r;
   let y2=Math.sin(angle+Math.PI)*r;

   let geo=new THREE.SphereGeometry(0.8);
   let m1=new THREE.Mesh(geo,new THREE.MeshPhongMaterial({color:cor(b1)}));
   let m2=new THREE.Mesh(geo,new THREE.MeshPhongMaterial({color:cor(b2)}));

   m1.position.set(x1,y1,z);
   m2.position.set(x2,y2,z);

   scene.add(m1);
   scene.add(m2);

   angle+=0.4;
 }

 function animate(){
   requestAnimationFrame(animate);
   scene.rotation.y+=0.01;
   renderer.render(scene,camera);
 }

 animate();
}

// ================= INIT =================
window.onload=initProteinViewer;
