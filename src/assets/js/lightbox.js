/**
 * Lightbox with Navigation for All Content Images
 * Église Saint-Martin de Villar-d'Arène
 *
 * Works on all images in <main> except:
 * - Logo images (.logo-img)
 * - Icons and small UI elements
 */

(function() {
  'use strict';

  // All clickable images on the page
  let galleryImages = [];
  let currentIndex = 0;

  // Create lightbox elements
  const lightbox = document.createElement('div');
  lightbox.className = 'lightbox';
  lightbox.innerHTML = `
    <span class="lightbox-close">&times;</span>
    <button class="lightbox-prev" aria-label="Image précédente">&#10094;</button>
    <img src="" alt="">
    <button class="lightbox-next" aria-label="Image suivante">&#10095;</button>
    <span class="lightbox-counter"></span>
  `;
  document.body.appendChild(lightbox);

  const lightboxImg = lightbox.querySelector('img');
  const closeBtn = lightbox.querySelector('.lightbox-close');
  const prevBtn = lightbox.querySelector('.lightbox-prev');
  const nextBtn = lightbox.querySelector('.lightbox-next');
  const counter = lightbox.querySelector('.lightbox-counter');

  // Check if an image should be clickable
  function isClickableImage(img) {
    // Skip logo and icons
    if (img.classList.contains('logo-img')) return false;
    if (img.closest('.logo-link')) return false;

    // Skip very small images (icons, decorations)
    if (img.naturalWidth && img.naturalWidth < 50) return false;
    if (img.naturalHeight && img.naturalHeight < 50) return false;

    // Must be inside main content
    if (!img.closest('main')) return false;

    return true;
  }

  // Collect all clickable images
  function collectImages() {
    galleryImages = Array.from(document.querySelectorAll('main img'))
      .filter(isClickableImage);
  }

  // Show image at index
  function showImage(index) {
    if (galleryImages.length === 0) return;

    // Wrap around
    if (index < 0) index = galleryImages.length - 1;
    if (index >= galleryImages.length) index = 0;

    currentIndex = index;
    const img = galleryImages[currentIndex];
    lightboxImg.src = img.src;
    lightboxImg.alt = img.alt || '';
    counter.textContent = `${currentIndex + 1} / ${galleryImages.length}`;

    // Hide navigation if only one image
    if (galleryImages.length <= 1) {
      prevBtn.style.display = 'none';
      nextBtn.style.display = 'none';
      counter.style.display = 'none';
    } else {
      prevBtn.style.display = '';
      nextBtn.style.display = '';
      counter.style.display = '';
    }
  }

  // Open lightbox
  function openLightbox(img) {
    collectImages();
    currentIndex = galleryImages.indexOf(img);
    if (currentIndex === -1) currentIndex = 0;

    showImage(currentIndex);
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  // Close lightbox
  function closeLightbox() {
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    lightboxImg.src = '';
  }

  // Navigate
  function showPrev() {
    showImage(currentIndex - 1);
  }

  function showNext() {
    showImage(currentIndex + 1);
  }

  // Event: Click on any main image
  document.addEventListener('click', function(e) {
    const img = e.target.closest('main img');
    if (img && isClickableImage(img)) {
      e.preventDefault();
      openLightbox(img);
    }
  });

  // Event: Navigation buttons
  prevBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    showPrev();
  });

  nextBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    showNext();
  });

  // Event: Close on click outside image
  lightbox.addEventListener('click', function(e) {
    if (e.target === lightbox || e.target === closeBtn) {
      closeLightbox();
    }
  });

  // Event: Keyboard navigation
  document.addEventListener('keydown', function(e) {
    if (!lightbox.classList.contains('active')) return;

    switch(e.key) {
      case 'Escape':
        closeLightbox();
        break;
      case 'ArrowLeft':
        showPrev();
        break;
      case 'ArrowRight':
        showNext();
        break;
    }
  });
})();
