function regularPlan() {
  return {
    legs: [
      { id: "north", capacity: 24, passengers: 18, stops: [{ id: "river" }] },
    ],
  };
}

function weatherPlan() {
  return {
    legs: [
      { id: "north", capacity: 20, passengers: 18, stops: [{ id: "river" }] },
    ],
  };
}

function sessionForWeatherService() {
  return require("../editor/stop_editor").createSession(regularPlan(), weatherPlan());
}

function oakEdit() {
  return { id: "entry-17", leg: "north", stop: { id: "oak" }, passengers: 3 };
}

module.exports = { regularPlan, weatherPlan, sessionForWeatherService, oakEdit };
