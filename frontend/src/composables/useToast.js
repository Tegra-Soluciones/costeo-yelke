import { reactive } from "vue";

export function useToast() {
  const toast = reactive({ show: false, msg: "", type: "success" });

  function showToast(msg, type = "success") {
    toast.msg = msg;
    toast.type = type;
    toast.show = true;
    setTimeout(() => (toast.show = false), 3500);
  }

  return { toast, showToast };
}
