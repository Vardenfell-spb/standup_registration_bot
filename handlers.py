
def button_compare(message_edit, keyboard2):
    button_coincidence = False
    if message_edit[1]:
        keyboard1 = message_edit[1].inline_keyboard
        if len(keyboard1) == len(keyboard2):
            for line_num, button_line in enumerate(keyboard2):
                if len(keyboard1[line_num]) == len(button_line):
                    for num, button in enumerate(button_line):
                        if button.text != keyboard1[line_num][num].text or \
                                button.callback_data != keyboard1[line_num][num].callback_data:
                            button_coincidence = True
                else:
                    button_coincidence = True
        else:
            button_coincidence = True
    else:
        button_coincidence = True
    return button_coincidence
