// eslint.config.js — Carbifyio Frontend ESLint Configuration (Flat config, ESLint 9+)
import js from "@eslint/js";

export default [
    js.configs.recommended,
    {
        files: ["src/**/*.js"],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: {
                // Browser globals
                window: "readonly",
                document: "readonly",
                localStorage: "readonly",
                fetch: "readonly",
                setTimeout: "readonly",
                clearTimeout: "readonly",
                URLSearchParams: "readonly",
                Chart: "readonly",
                console: "readonly",
                URL: "readonly",
            },
        },
        rules: {
            "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
            "no-console": ["warn", { allow: ["warn", "error"] }],
            "eqeqeq": ["error", "always"],
            "no-var": "error",
            "prefer-const": "error",
            "prefer-template": "error",
            "no-duplicate-imports": "error",
            "no-shadow": "error",
            "curly": ["error", "all"],
        },
    },
    {
        // Relax rules for test files
        files: ["src/**/*.test.js", "tests/**/*.test.js"],
        languageOptions: {
            globals: {
                describe: "readonly",
                it: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                vi: "readonly",
            },
        },
        rules: {
            "no-console": "off",
        },
    },
];
