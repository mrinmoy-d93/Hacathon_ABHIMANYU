/**
 * Acronym expansion registry for FRS FR-4.5 / AC-7.
 * Every domain-specific acronym is expanded on its first occurrence per screen.
 */
export const ACRONYMS: Record<string, string> = {
  AI: "Artificial Intelligence",
  ML: "Machine Learning",
  API: "Application Programming Interface",
  GAN: "Generative Adversarial Network",
  OTP: "One-Time Password",
  NGO: "Non-Governmental Organisation",
  PII: "Personally Identifiable Information",
  "2FA": "Two-Factor Authentication",
  JWT: "JSON Web Token",
  KHJ: "KHOJO case reference prefix",
  CSV: "Comma-Separated Values",
  SMS: "Short Message Service",
  HMAC: "Hash-based Message Authentication Code",
  FRS: "Functional Requirements Specification",
};

export function expand(short: string): string {
  const full = ACRONYMS[short];
  return full ? `${full} (${short})` : short;
}
