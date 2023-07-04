<script setup lang="ts">

defineProps<{
  modelValue: Date | undefined,
}>();
const emit = defineEmits<{
  (event: "update:modelValue", value: Date | undefined): void,
}>();

function onInput(event: any) {
  emit("update:modelValue", event.target?.value ? new Date(event.target.value) : undefined);
}
function format(date: Date | undefined) {
  // this seems to actually be the best way to do this
  // https://stackoverflow.com/q/23593052/1850609
  return date && new Date(date.getTime()-(date.getTimezoneOffset()*60*1000)).toISOString().split("Z")[0];
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
