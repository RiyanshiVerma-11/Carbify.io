// vitest.config.js — Carbifyio Frontend Test Configuration
import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        // Use jsdom so DOM APIs (document, window, localStorage) work in tests
        environment: "jsdom",
        globals: true,
        // Test file patterns
        include: ["src/**/*.test.js", "tests/**/*.test.js"],
        coverage: {
            provider: "v8",
            reporter: ["text", "lcov", "html"],
            include: ["src/js/**/*.js"],
            exclude: ["src/js/constants.js"],
        },
    },
});
