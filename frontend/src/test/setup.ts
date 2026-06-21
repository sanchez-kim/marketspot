import "@testing-library/jest-dom";

// jsdom does not implement scrollTo — provide a no-op so components using
// ref.scrollTo() don't throw in tests.
Element.prototype.scrollTo = () => {};
