import { createApp } from "https://unpkg.com/petite-vue@0.2.2/dist/petite-vue.es.js"


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

async function send_request(content) {
    var response = await fetch("/admin/users/edit", {
        "method": "POST",
        "headers": {"Content-type": "application/json"},
        "body": JSON.stringify(content),
    })
    if (response.ok) {
        return response.json()
    }
}

async function toggle_admin(event) {
    var row = event.currentTarget.closest("tr")
    var data = row.dataset;
    var response = await send_request({"id": data.uid, "is_admin": !bool(data.is_admin)})
    if (response) {
        data.is_admin = response.is_admin

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
            var check_icon = row.children[0].children[1];
            row.children[0].removeChild(check_icon);
        }
    }
    
}

async function show_edit(event) {
    var row = event.currentTarget.closest("tr")
    var data = row.dataset

    var name_field = document.getElementById("input-name").content.cloneNode(true)
    name_field.querySelector("input").setAttribute("placeholder", data.name)
    row.children[0].children[0].replaceWith(name_field)
    name_field.addEventListener("keypress", async (event) => {
        console.log(event.key)
        if (event.key === "Enter") {
            submit_edit(event)
        }
    })

    var email_field = document.getElementById("input-email").content.cloneNode(true)
    email_field.querySelector("input").setAttribute("placeholder", data.email)
    row.children[1].children[0].replaceWith(email_field)
    email_field.addEventListener("keypress", async (event) => {
        if (event.key === "Enter") {
            submit_edit(event)
        }
    })

    event.currentTarget.removeEventListener("click", show_edit)
    event.currentTarget.addEventListener("click", submit_edit)
}

async function submit_edit(event) {
    var row = event.currentTarget.closest("tr")
    var button = event.currentTarget
    var data = row.dataset

    var name_field = row.children[0].children[0]
    var email_field = row.children[1].children[0]

    var response = await send_request({"id": data.uid, "name": name_field.value, "email": email_field.value})
    if (response) {
        data.name = response.name
        data.email = response.email

        var name_str = document.createElement("span")
        name_str.innerHTML = data.name + " "
        name_field.replaceWith(name_str)
        var email_str = document.createElement("span")
        email_str.innerHTML = data.email
        email_field.replaceWith(email_str)

        button.removeEventListener("click", submit_edit)
        button.addEventListener("click", show_edit)
    }
}






function swap_admin() {
    this.user.is_admin = !this.user.is_admin
}



function TableRow(user) {
    return {
        $template: "#table_row",
        user: user,
    }
}


createApp({
    $delimeters: ["${", "}"],
    TableRow,
}).mount()

