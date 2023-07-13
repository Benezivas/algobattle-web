<script setup lang="ts">

defineProps<{
  modelValue: Date | undefined,
}>();
const emit = defineEmits<{
  (event: "update:modelValue", value: Date | undefined): void,
}>();

function onInput(event: any) {
  let date = new Date(event.target.value);
  // we convert it to UTC here, this way all timestamps are in UTC everywhere
  // the frontend displays them as ISO strings, i.e. in UTC, and the backend treats them as timezone unaware
  // thus we can always enter times and have them be treated as being in the server's local timezone
  date = new Date(date.getTime() - (date.getTimezoneOffset()*60*1000));
  emit("update:modelValue", event.target?.value ? date : undefined);
}
function format(date: Date | undefined) {
  // this seems to actually be the best way to do this
  // https://stackoverflow.com/q/23593052/1850609
  return date && new Date(date.getTime()).toISOString().split("Z")[0];
}
</script>

<template>
  <input
    class="form-control"
    type="datetime-local"
    ref="input"
    :value="format(modelValue)"
    @input="onInput"
  >
</template>
