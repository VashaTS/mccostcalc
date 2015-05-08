window.onload = rolloverInit;

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

function addItem(tid) {
	if (document.getElementById('f1').style.display == 'none') {
		document.getElementById('f1').style.display = 'block';
		document.getElementById('f1img').src = "gfx/" + tid + ".png";
		document.getElementById('f1hi').value=tid;
	}
	else if (document.getElementById('f2').style.display == 'none') {
		document.getElementById('f2').style.display = 'block';
		document.getElementById('f2img').src = "gfx/" + tid + ".png";
		document.getElementById('f2hi').value=tid;
	}
	else if (document.getElementById('f3').style.display == 'none') {
		document.getElementById('f3').style.display = 'block';
		document.getElementById('f3img').src = "gfx/" + tid + ".png";
		document.getElementById('f3hi').value=tid;
	}
	else if (document.getElementById('f4').style.display == 'none') {
		document.getElementById('f4').style.display = 'block';
		document.getElementById('f4img').src = "gfx/" + tid + ".png";
		document.getElementById('f4hi').value=tid;
	}
	else if (document.getElementById('f5').style.display == 'none') {
		document.getElementById('f5').style.display = 'block';
		document.getElementById('f5img').src = "gfx/" + tid + ".png";
		document.getElementById('f5hi').value=tid;
	}
	else if (document.getElementById('f6').style.display == 'none') {
		document.getElementById('f6').style.display = 'block';
		document.getElementById('f6img').src = "gfx/" + tid + ".png";
		document.getElementById('f6hi').value=tid;
	}
	else if (document.getElementById('f7').style.display == 'none') {
		document.getElementById('f7').style.display = 'block';
		document.getElementById('f7img').src = "gfx/" + tid + ".png";
		document.getElementById('f7hi').value=tid;
	}
	else if (document.getElementById('f8').style.display == 'none') {
		document.getElementById('f8').style.display = 'block';
		document.getElementById('f8img').src = "gfx/" + tid + ".png";
		document.getElementById('f8hi').value=tid;
	}
}
function displayBl(aid) {
	document.getElementById("it_blocks").style.display = 'none';
	document.getElementById("it_potions").style.display = 'none';
	document.getElementById("i"+aid).style.display = 'block';
}
function hideLine(lid) {
	document.getElementById(lid).style.display = 'none';
	document.getElementById(lid+"f").value='';
}

function btnh(iid) {
	document.getElementById(iid).className="formbtnh";
}
function btnd(iid) {
	document.getElementById(iid).className="formbtn";
}
