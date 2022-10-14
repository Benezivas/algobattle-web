
function bool(stringValue) {
    switch(stringValue.toLowerCase().trim()){
        case "true": 
        case "yes": 
        case "1": 
          return true;

        case "false": 
        case "no": 
        case "0":
        case "none":
        case null: 
        case undefined:
          return false;

        default: 
          return JSON.parse(stringValue);
    }
}

async function toggle_admin(event) {
    var row = event.currentTarget.closest("tr")
    var data = row.dataset;
    var response = await fetch("/admin/users/edit", {
        "method": "POST",
        "headers": {"Content-type": "application/json"},
        "body": JSON.stringify({"id": data.uid, "is_admin": !bool(data.is_admin)}),
    });
    if (response.ok) {
        data.is_admin = !bool(data.is_admin);

        var admin_button_icon = row.children[3].children[0].children[0].children[0];
        if (bool(data.is_admin)) {
            admin_button_icon.classList.replace("bi-patch-plus", "bi-patch-minus");
        } else {
            admin_button_icon.classList.replace("bi-patch-minus", "bi-patch-plus");
        }
        if (bool(data.is_admin)) {
            var check_icon = document.getElementById("admin-check").content.cloneNode(true);
            row.children[0].appendChild(check_icon);
        } else {
            var check_icon = row.children[0].children[0];
            row.children[0].removeChild(check_icon);
        }
    }
    
}

document.addEventListener("DOMContentLoaded", () => {
    for (var button of document.getElementsByClassName("user-toggle-admin")) {
        button.addEventListener("click", toggle_admin);
    }    
})