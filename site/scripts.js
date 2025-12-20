document.addEventListener('DOMContentLoaded',()=>{
  const navToggle=document.getElementById('navToggle');
  const navLinks=document.getElementById('navLinks');
  navToggle?.addEventListener('click',()=>{
    navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
  })
})
