import "@testing-library/jest-dom";

// jsdom does not implement scrollTo — provide a no-op so components using
// ref.scrollTo() don't throw in tests.
Element.prototype.scrollTo = () => {};

// jsdom does not implement matchMedia — components using useIsMobile() call it
// at render. Default to "not matching" (desktop) so existing tests render the
// desktop layout; tests that need the phone branch mock useIsMobile directly.
window.matchMedia =
  window.matchMedia ||
  ((query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }));
