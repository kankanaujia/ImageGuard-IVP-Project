import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

// eslint-config-next 15 ships legacy configs, so load them through FlatCompat.
const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Analysis results are loosely structured JSON from the API.
      "@typescript-eslint/no-explicit-any": "warn",
      // Evidence images come from the local API, not next/image's optimizer.
      "@next/next/no-img-element": "off",
    },
  },
  { ignores: [".next/**", "out/**", "build/**", "next-env.d.ts"] },
];
