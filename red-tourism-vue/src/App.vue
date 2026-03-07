<template>
  <div id="app">
    <Dashboard />
  </div>
</template>

<script>
import Dashboard from "./views/Dashboard.vue"

export default {
  name: "App",
  components: {
    Dashboard
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  width: 100%;
}
</style>
