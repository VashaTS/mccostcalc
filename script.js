function rolloverInit() {
	for (var i=0; i<document.images.length; i++) {
		if (document.images[i].parentNode.tagName == "A") {
			setupRollover(document.images[i]);
		}
	}
}
function setupRollover(thisImage) {
	thisImage.outImage = new Image();
	thisImage.outImage.src = thisImage.src;
	thisImage.onmouseout = function() {
		this.src = this.outImage.src;
	}
	thisImage.overImage = new Image();
	thisImage.overImage.src = "gfx/" + thisImage.id + "_on.png";
	thisImage.onmouseover = function() {
		this.src = this.overImage.src;
	}
}

function addItem(tid,rtid,rn) {
	if (document.getElementById('f1').style.display == 'none') {
		document.getElementById('f1').style.display = 'block';
		document.getElementById('f1img').src = "gfx/" + tid + ".png";
		document.getElementById('f1img').title = rn;
		document.getElementById('f1hi').value=rtid;
	}
	else if (document.getElementById('f2').style.display == 'none') {
		document.getElementById('f2').style.display = 'block';
		document.getElementById('f2img').src = "gfx/" + tid + ".png";
		document.getElementById('f2img').title = rn;
		document.getElementById('f2hi').value=rtid;
	}
	else if (document.getElementById('f3').style.display == 'none') {
		document.getElementById('f3').style.display = 'block';
		document.getElementById('f3img').src = "gfx/" + tid + ".png";
		document.getElementById('f3img').title = rn;
		document.getElementById('f3hi').value=rtid;
	}
	else if (document.getElementById('f4').style.display == 'none') {
		document.getElementById('f4').style.display = 'block';
		document.getElementById('f4img').src = "gfx/" + tid + ".png";
		document.getElementById('f4img').title = rn;
		document.getElementById('f4hi').value=rtid;
	}
	else if (document.getElementById('f5').style.display == 'none') {
		document.getElementById('f5').style.display = 'block';
		document.getElementById('f5img').src = "gfx/" + tid + ".png";
		document.getElementById('f5img').title = rn;
		document.getElementById('f5hi').value=rtid;
	}
	else if (document.getElementById('f6').style.display == 'none') {
		document.getElementById('f6').style.display = 'block';
		document.getElementById('f6img').src = "gfx/" + tid + ".png";
		document.getElementById('f6img').title = rn;
		document.getElementById('f6hi').value=rtid;
	}
	else if (document.getElementById('f7').style.display == 'none') {
		document.getElementById('f7').style.display = 'block';
		document.getElementById('f7img').src = "gfx/" + tid + ".png";
		document.getElementById('f7img').title = rn;
		document.getElementById('f7hi').value=rtid;
	}
	else if (document.getElementById('f8').style.display == 'none') {
		document.getElementById('f8').style.display = 'block';
		document.getElementById('f8img').src = "gfx/" + tid + ".png";
		document.getElementById('f8img').title = rn;
		document.getElementById('f8hi').value=rtid;
	}
	else if (document.getElementById('f9').style.display == 'none') {
		document.getElementById('f9').style.display = 'block';
		document.getElementById('f9img').src = "gfx/" + tid + ".png";
		document.getElementById('f9img').title = rn;
		document.getElementById('f9hi').value=rtid;
	}
	else if (document.getElementById('f10').style.display == 'none') {
		document.getElementById('f10').style.display = 'block';
		document.getElementById('f10img').src = "gfx/" + tid + ".png";
		document.getElementById('f10img').title = rn;
		document.getElementById('f10hi').value=rtid;
	}
}
function displayBl(aid) {
	document.getElementById("it_blocks").style.display = 'none';
	document.getElementById("it_items").style.display = 'none';
	document.getElementById("it_potions").style.display = 'none';
	document.getElementById("it_redstone").style.display = 'none';
	document.getElementById("it_colored").style.display = 'none';
	document.getElementById("it_sets").style.display = 'none';
	document.getElementById("i"+aid).style.display = 'block';
}
function hideLine(lid) {
	document.getElementById(lid).style.display = 'none';
	document.getElementById(lid+"f").value='';
	document.getElementById(lid+"hi").value='';
}

function btnh(iid) {
	document.getElementById(iid).className="formbtnh";
}
function btnd(iid) {
	document.getElementById(iid).className="formbtn";
}
function imgh(iid) {
	document.getElementById(iid).className="hgl";
}
function imgd(iid) {
	document.getElementById(iid).className="nrm";
}
function ajaxsubmit() {
	$.ajax({
		type: "POST",
		url: "index.php?process=yes",
		dataType: "html",
		data: $('#things').serialize(), 
		success: function(response){
			$("#resultdiv").html(response);
		}
	});
}
