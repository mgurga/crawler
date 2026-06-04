console.log("script loaded");

const canvas = document.getElementById("indexcanvas");
const ctx = canvas.getContext("2d");

canvas.setAttribute("height", document.getElementsByTagName("body")[0].clientHeight);
canvas.setAttribute("width", 230);

function draw() {
    requestAnimationFrame(draw);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    var results = document.getElementsByClassName("result");

    for (var i = 0; i < results.length; i++) {
        var ele = results[i];
        var indexy = ele.getBoundingClientRect().y + window.scrollY;
        indexy += ele.getBoundingClientRect().height / 2;
        var indexrad = ele.getBoundingClientRect().height / 2;

        if (i != results.length - 1) {
            var middley = results[i + 1].getBoundingClientRect().y + window.scrollY;
            middley += results[i + 1].getBoundingClientRect().height / 2;
            middley = (indexy + middley) / 2;
            var arcrad = middley - indexy

            ctx.beginPath();
            if (i % 2 == 0) {
                ctx.arc((canvas.width / 5)*2, middley, arcrad, 0.5 * Math.PI, 1.5 * Math.PI);
            } else {
                ctx.arc((canvas.width / 5)*3, middley, arcrad, 1.5 * Math.PI, 0.5 * Math.PI);
            }
            ctx.strokeStyle = "black";
            ctx.stroke()
        }

        var indexshrink = 0;
        if (i > Math.floor(results.length / 2)) {
            indexshrink = (i - Math.floor(results.length / 2)) * 2;
        }

        // ctx.beginPath();
        // ctx.moveTo(0, indexy);
        // ctx.lineTo(canvas.width, indexy);
        // ctx.stroke();

        ctx.beginPath();
        ctx.arc((canvas.width / 2), indexy, indexrad - indexshrink, 0, 2 * Math.PI);
        ctx.fillStyle = "white";
        ctx.fill();
        ctx.strokeStyle = "black";
        ctx.stroke();

        ctx.fillStyle = "black";
        ctx.font = "italic 40pt Kode Mono";
        ctx.textBaseline = "middle";
        ctx.textAlign = "center";
        ctx.fillText("#" + (i + 1), (canvas.width / 2), indexy);
    }
}

draw();
