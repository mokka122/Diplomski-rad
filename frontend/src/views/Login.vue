<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";

import {
  useRoute,
  useRouter,
} from "vue-router";

import {
  getGoogleClientId,
  loadGoogleIdentityScript,
  loginWithGoogle,
} from "../services/auth";


const router = useRouter();
const route = useRoute();

const googleButton = ref(null);

const isSigningIn = ref(false);
const loginError = ref("");

let googleReady = false;
let resizeTimer = null;


async function handleCredentialResponse(
  response,
) {
  if (!response?.credential) {
    loginError.value =
      "Google did not return a valid credential.";

    return;
  }

  isSigningIn.value = true;
  loginError.value = "";

  try {
    await loginWithGoogle(
      response.credential,
    );

    const destination =
      typeof route.query.redirect ===
      "string"
        ? route.query.redirect
        : "/";

    await router.replace(
      destination,
    );
  } catch (error) {
    loginError.value =
      error.message;
  } finally {
    isSigningIn.value = false;
  }
}


function getGoogleButtonWidth() {
  if (!googleButton.value) {
    return 280;
  }

  const width =
    googleButton.value
      .getBoundingClientRect()
      .width;

  return Math.max(
    200,
    Math.floor(width),
  );
}


function renderGoogleButton() {
  if (
    !googleReady ||
    !googleButton.value ||
    !window.google
      ?.accounts
      ?.id
  ) {
    return;
  }

  googleButton.value
    .replaceChildren();

  window.google.accounts.id
    .renderButton(
      googleButton.value,
      {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
        width:
          getGoogleButtonWidth(),
      },
    );
}


function handleWindowResize() {
  if (resizeTimer) {
    clearTimeout(
      resizeTimer,
    );
  }

  resizeTimer =
    setTimeout(
      () => {
        renderGoogleButton();
      },
      120,
    );
}


async function initializeGoogleLogin() {
  try {
    await loadGoogleIdentityScript();

    await nextTick();

    window.google.accounts.id
      .initialize({
        client_id:
          getGoogleClientId(),

        callback:
          handleCredentialResponse,

        auto_select: false,

        cancel_on_tap_outside:
          true,
      });

    googleReady = true;

    renderGoogleButton();
  } catch (error) {
    loginError.value =
      error.message;
  }
}


onMounted(async () => {
  await initializeGoogleLogin();

  window.addEventListener(
    "resize",
    handleWindowResize,
  );
});


onBeforeUnmount(() => {
  window.removeEventListener(
    "resize",
    handleWindowResize,
  );

  if (resizeTimer) {
    clearTimeout(
      resizeTimer,
    );
  }
});
</script>


<template>
  <main class="login-page">
    <section class="login-layout">
      <div class="login-copy">
        <img
          class="login-logo"
          src="/logo.png"
          alt="OceanEye"
        />

        <div class="login-heading">
          <p class="eyebrow">
            REAL-TIME MARITIME INTELLIGENCE
          </p>

          <h1>
            Maritime activity,
            <span>
              made visible.
            </span>
          </h1>

          <p class="login-description">
            Monitor vessel movements, live traffic
            activity and predictive maritime insights
            from a single operational dashboard.
          </p>
        </div>

        <div class="login-footer-note">
          Ålesund Maritime Area · Norway
        </div>
      </div>

      <div class="login-access-column">
        <div class="login-visual">
          <div
            class="
              login-radar-ring
              login-radar-ring-one
            "
          ></div>

          <div
            class="
              login-radar-ring
              login-radar-ring-two
            "
          ></div>

          <div
            class="
              login-radar-ring
              login-radar-ring-three
            "
          ></div>

          <div class="login-radar-line"></div>

          <span
            class="
              login-vessel-dot
              login-vessel-dot-one
            "
          ></span>

          <span
            class="
              login-vessel-dot
              login-vessel-dot-two
            "
          ></span>

          <span
            class="
              login-vessel-dot
              login-vessel-dot-three
            "
          ></span>

          <div class="login-ship-symbol">
            <svg
              viewBox="0 0 64 72"
              aria-hidden="true"
            >
              <path
                d="
                  M32 4
                  L54 56
                  L32 48
                  L10 56
                  Z
                "
                fill="currentColor"
              />

              <path
                d="M32 13 V49"
                stroke="white"
                stroke-width="3"
                stroke-linecap="round"
                opacity="0.9"
              />
            </svg>
          </div>

          <div class="login-area-label">
            <span>
              LIVE AREA
            </span>

            <strong>
              Ålesund
            </strong>

            <small>
              62.47° N · 6.15° E
            </small>
          </div>
        </div>

        <div class="login-card">
          <div class="login-card-heading">
            <p class="eyebrow">
              SECURE ACCESS
            </p>

            <h2>
              Welcome to OceanEye
            </h2>

            <p>
              Sign in with your Google account to
              continue to the maritime monitoring
              dashboard.
            </p>
          </div>

          <div class="google-auth-area">
            <div
              ref="googleButton"
              class="google-button-container"
            ></div>

            <p
              v-if="isSigningIn"
              class="google-auth-message"
            >
              Signing you in...
            </p>

            <p
              v-if="loginError"
              class="
                google-auth-message
                google-auth-message--error
              "
            >
              {{ loginError }}
            </p>
          </div>

          <div class="login-security-note">
            <span
              class="security-dot"
            ></span>

            Authentication will be verified
            securely by the OceanEye backend.
          </div>
        </div>
      </div>
    </section>
  </main>
</template>