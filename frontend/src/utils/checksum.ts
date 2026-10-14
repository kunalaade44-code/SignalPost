const MOD11_WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2];

export interface ChecksumResult {
  isValid: boolean;
  clean: string;
  expectedControl: number | null;
  message: string;
}

export function validateNorwegianOrgNumber(raw: string): ChecksumResult {
  const clean = raw.replace(/[\s.-]/g, '');

  if (!clean) {
    return { isValid: false, clean: '', expectedControl: null, message: 'Enter a 9-digit Norwegian organization number' };
  }

  if (!/^\d+$/.test(clean)) {
    return { isValid: false, clean, expectedControl: null, message: 'Only digits allowed' };
  }

  if (clean.length < 8) {
    return {
      isValid: false,
      clean,
      expectedControl: null,
      message: `${9 - clean.length} more digits needed`,
    };
  }

  const digits = clean.split('').map(Number);
  const weightedSum = digits.slice(0, 8).reduce((acc, d, i) => acc + d * MOD11_WEIGHTS[i], 0);
  const remainder = weightedSum % 11;

  let expectedControl: number;
  if (remainder === 0) {
    expectedControl = 0;
  } else if (remainder === 1) {
    return {
      isValid: false,
      clean,
      expectedControl: null,
      message: 'Invalid number sequence (remainder 1)',
    };
  } else {
    expectedControl = 11 - remainder;
  }

  if (clean.length === 8) {
    return {
      isValid: false,
      clean,
      expectedControl,
      message: `8 digits entered. Expected 9th checksum digit: ${expectedControl}`,
    };
  }

  if (clean.length === 9) {
    const actualControl = digits[8];
    if (actualControl === expectedControl) {
      return {
        isValid: true,
        clean,
        expectedControl,
        message: 'Valid Norwegian organization number (Mod-11 verified)',
      };
    } else {
      return {
        isValid: false,
        clean,
        expectedControl,
        message: `Checksum mismatch: 9th digit is ${actualControl}, expected ${expectedControl}`,
      };
    }
  }

  return {
    isValid: false,
    clean,
    expectedControl: null,
    message: `Too many digits (${clean.length}/9)`,
  };
}
