
function reveal() {
    var reveals = document.querySelectorAll(".reveal");
    var areaHeight = window.innerHeight;
  
    for (var i = 0; i < reveals.length; i++) {
      var areaTop = reveals[i].getBoundingClientRect().top;
      var areaBottom = areaTop + reveals[i].clientHeight;
  
      if (areaTop < areaHeight && areaBottom >= 0) {
        reveals[i].classList.add("active");
      } else {
        reveals[i].classList.remove("active");
      }
    }
  }
  
  // Trigger the reveal function on page load and scroll
  window.addEventListener("load", reveal);
  window.addEventListener("scroll", reveal);
  