/**
 * Django Auth Portal - Main JavaScript
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Resend Verification Code Countdown Logic
  const resendBtn = document.getElementById("resend-btn");
  const countdownContainer = document.getElementById("countdown-container");
  const countdownTimer = document.getElementById("countdown-timer");

  if (resendBtn && countdownTimer) {
    let remainingSeconds = parseInt(countdownTimer.getAttribute("data-seconds"), 10) || 0;

    function updateCountdownUI() {
      if (remainingSeconds > 0) {
        resendBtn.disabled = true;
        countdownTimer.textContent = remainingSeconds;
        if (countdownContainer) {
          countdownContainer.style.display = "inline-block";
        }
        remainingSeconds--;
        setTimeout(updateCountdownUI, 1000);
      } else {
        resendBtn.disabled = false;
        if (countdownContainer) {
          countdownContainer.style.display = "none";
        }
      }
    }

    if (remainingSeconds > 0) {
      updateCountdownUI();
    } else {
      resendBtn.disabled = false;
      if (countdownContainer) {
        countdownContainer.style.display = "none";
      }
    }
  }

  // 2. Numeric-Only Filter for 6-Digit Verification Input
  const verifyInput = document.querySelector(".verification-input");
  if (verifyInput) {
    verifyInput.addEventListener("input", function (e) {
      // Strip non-digits
      this.value = this.value.replace(/\D/g, "").slice(0, 6);
    });

    // Auto submit form when 6 digits are typed
    verifyInput.addEventListener("keyup", function (e) {
      if (this.value.length === 6) {
        const form = this.closest("form");
        if (form) {
          form.submit();
        }
      }
    });
  }

  // 3. Auto-dismiss alert messages after 7 seconds
  const autoAlerts = document.querySelectorAll(".alert-dismissible");
  autoAlerts.forEach(function (alertElement) {
    setTimeout(function () {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertElement);
        bsAlert.close();
      } catch (err) {
        // Fallback if bootstrap JS is not loaded yet
        alertElement.style.display = "none";
      }
    }, 7000);
  });
});
