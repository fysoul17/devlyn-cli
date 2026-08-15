"use strict";

const { runCourierAssignerTest } = require("./courier_assigner_test");
const { runRefusalCaseTest } = require("./refusal_case_test");

runCourierAssignerTest();
runRefusalCaseTest();
console.log("checks passed");
