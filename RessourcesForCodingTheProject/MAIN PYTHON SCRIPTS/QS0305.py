print("- Quick Search - ver. 0305 (By Neil)")
print("- Quick Search - ver. 0305 (By Neil)")
print("- Quick Search - ver. 0305 (By Neil)")
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, colorchooser, font
import pandas as pd
print("Loading... Please wait...")
import re
import threading
import pickle
import os
import sys
import pyperclip
import time
import traceback
import tempfile
import json
import csv
print("All done !")

try:
    import pyi_splash
    splash_active = True
except ImportError:
    splash_active = False

# At the top with other global variables
search_query = ""
search_match_type = "contains"
search_start_index = 0


# Global variables
global split_dict, whole_dict, search_results, current_index, limit, ref_split_dict
global ref_whole_dict, reference_active, font_settings, color_buttons

# Available games and languages
GAMES = ['BDO', 'BDM', 'BDC', 'OTHER']
LANGUAGES = ['DE', 'EN', 'ES', 'SP', 'FR', 'ID', 'JP', 'PT', 'RU', 'TR', 'TH', 'TW', 'CH']

# Default font settings
font_settings = {
    'family': 'Arial',
    'size': 10,
    'ui_language': 'English',  # Add this line
    'colors': {
        'korean': '#000000',
        'translation': '#000000',
        'reference': '#000000'
    },
    'styles': {
        'korean': '',
        'translation': '',
        'reference': ''
    }
}

# UI Language settings
UI_LANGUAGES = {
    'English': {
        'language_select': "Language Selection",
        'global_font': "Global Font Settings",
        'select_font': "Select Font:",
        'select_size': "Select Size:",
        'korean_text': "Korean Text:",
        'translated_text': "Translated Text:",
        'reference_text': "Reference Text:",
        'settings_title': "Settings",
        'font_settings': "Font Settings",
        'font_family': "Font Family:",
        'font_size': "Font Size:",
        'reset_font': "Reset Font Settings",
        'color_settings': "Color Settings",
        'korean_color': "Korean Color",
        'translation_color': "Translation Color",
        'reference_color': "Reference Color",
        'reset_color': "Reset Color Settings",
        'style_settings': "Style Settings",
        'bold': "Bold",
        'italic': "Italic",
        'reset_style': "Reset Style Settings",
        'create_dict': "Create Dictionary",
        'load_dict': "Load Dictionary",
        'reference_off': "REFERENCE OFF",
        'settings': "Settings",
        'search': "Search",
        'contains': "Contains",
        'exact_match': "Exact Match",
        'load_more': "Load More Results",
        'one_line': "One Line",
        'multi_line': "Multi Line",
        'reference_with_lang': "REFERENCE: {game}-{lang}",
        'loaded_dict': "LOADED: {game}-{lang}",
        'loaded_dict_kr': "사용 중: {game}-{lang}",
        'platform_select': "Platform Selection",
        'new_terms_glossary': "New Terms Glossary",
        'glossary_crosscheck': "Glossary Crosscheck",
        'glossary_crosscheck_selection': "Glossary Crosscheck",
        'start_crosscheck': "Start",
        'file_upload': "File Upload",
        'select_language_data': "Select Language Data File",
        'select_close_data': "Select Close Data File",
        'language_data_uploaded': "Language Data - Uploaded",
        'close_data_uploaded': "Close Data - Uploaded",
        'glossary_base_selection': "Glossary Base Selection",
        'use_language_data': "Use Language Data",
        'use_close_data': "Use Close Data",
        'use_both_combined': "Use Both Combined",
        'check_language_data': "Check Language Data",
        'check_close_data': "Check Close Data",
        'check_both_combined': "Check Both Combined"
    },
    '한국어': {
        'language_select': "언어 선택",
        'global_font': "전체 폰트 설정",
        'select_font': "폰트 선택:",
        'select_size': "크기 선택:",
        'korean_text': "원문:",
        'translated_text': "번역문:",
        'reference_text': "참조문:",
        'settings_title': "설정",
        'font_settings': "폰트 설정",
        'font_family': "폰트:",
        'font_size': "크기:",
        'reset_font': "폰트 설정 초기화",
        'color_settings': "색상 설정",
        'korean_color': "원문 색상",
        'translation_color': "번역문 색상",
        'reference_color': "참조문 색상",
        'reset_color': "색상 설정 초기화",
        'style_settings': "스타일 설정",
        'bold': "굵게",
        'italic': "기울임",
        'reset_style': "스타일 설정 초기화",
        'create_dict': "사전 생성",
        'load_dict': "사전 불러오기",
        'reference_off': "참조 OFF",
        'settings': "설정",
        'search': "검색",
        'contains': "포함",
        'exact_match': "정확히 일치",
        'load_more': "더 보기",
        'one_line': "일반 검색",
        'multi_line': "멀티 검색",
        'reference_with_lang': "참조: {game}-{lang}",
        'loaded_dict': "사용 중: {game}-{lang}",
        'loaded_dict_kr': "사용 중: {game}-{lang}",
        'platform_select': "플랫폼 선택",
        'new_terms_glossary': "신규 명칭 글로서리 생성",
        'glossary_crosscheck': "명칭 자동 크로스체크",
        'glossary_crosscheck_selection': "크로스체크",
        'start_crosscheck': "시작",
        'file_upload': "파일 업로드",
        'select_language_data': "렝귀지 데이터 파일 선택",
        'select_close_data': "클로즈 데이터 파일 선택",
        'language_data_uploaded': "렝귀지 데이터 - 업로드됨",
        'close_data_uploaded': "클로즈 데이터 - 업로드됨",
        'glossary_base_selection': "글로서리 기준 선택",
        'use_language_data': "렝귀지 데이터 사용",
        'use_close_data': "클로즈 데이터 사용",
        'use_both_combined': "두 데이터 모두 사용",
        'check_language_data': "렝귀지 데이터 체크",
        'check_close_data': "클로즈 데이터 체크",
        'check_both_combined': "두 데이터 모두 체크"

    }
}

# Default UI language
current_ui_language = 'English'
settings_window_instance = None

# Initialize selected cells and last selected cell
selected_cells = set()
last_selected_cell = None

### Core Utility Functions ###
def tokenize(text):
    if isinstance(text, str) and text.strip() != '' and '\t' not in text:
        return re.split(r'\\?\\n|\n', text)
    else:
        return []

def post_process_newlines(text):
    return str(text).replace("\\n", "\n")
    
    
    
def normalize_dictionary_text(text):
    if not isinstance(text, str):
        return ""
    
    # First, handle unmatched quotation marks by identifying balanced pairs
    balanced_indices = set()
    quote_indices = [i for i, char in enumerate(text) if char == '"']
    
    # Greedily match quotes from left to right in pairs
    for i in range(0, len(quote_indices) - 1, 2):
        balanced_indices.add(quote_indices[i])
        balanced_indices.add(quote_indices[i + 1])
    
    # Create a new string without unmatched quotes
    result = []
    for i, char in enumerate(text):
        if char == '"' and i not in balanced_indices:
            continue  # Skip this unmatched quote
        result.append(char)
    
    # Convert back to string
    text = ''.join(result)
    
    # Normalize all Unicode whitespace variants
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]+', ' ', text)  # Unicode spaces including NBSP
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E]+', '', text)  # Remove zero-width and directional characters
    
    # Normalize apostrophes to straight apostrophe
    text = re.sub(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]', "'", text)
    
    # Normalize remaining whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

### Style and Settings Functions ###
def save_settings():
    try:
        with open('qs_settings.json', 'w') as f:
            json.dump(font_settings, f)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

def load_settings():
    global font_settings, current_ui_language
    try:
        with open('qs_settings.json', 'r') as f:
            loaded_settings = json.load(f)
            font_settings.update(loaded_settings)
            if 'ui_language' in loaded_settings:
                current_ui_language = loaded_settings['ui_language']
                # Update UI elements with loaded language
                change_ui_language(current_ui_language)
            if 'color_buttons' in globals():
                for text_type, button in color_buttons.items():
                    apply_color_to_button(button, font_settings['colors'][text_type])
    except FileNotFoundError:
        # Initialize ui_language in font_settings if not present
        font_settings['ui_language'] = current_ui_language
        save_settings()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load settings: {str(e)}")

def apply_color_to_button(button, color):
    r, g, b = tuple(int(color[1:][i:i+2], 16) for i in (0, 2, 4))
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    text_color = 'white' if brightness < 128 else 'black'
    button.config(bg=color, fg=text_color)

def choose_color(text_type):
    color = colorchooser.askcolor(color=font_settings['colors'][text_type])[1]
    if color:
        font_settings['colors'][text_type] = color
        apply_color_to_button(color_buttons[text_type], color)
        save_settings()
        update_text_display()


def update_settings_window(settings_window):
    """Updates all text in the settings window to the current language"""
    if not settings_window:
        return
        
    # Update window title
    settings_window.title(UI_LANGUAGES[current_ui_language]['settings_title'])
    
    # Update all LabelFrames and their children
    for child in settings_window.winfo_children():
        if isinstance(child, ttk.LabelFrame):
            # Update language frame
            if any(x in child.cget('text') for x in ['Language', '언어']):
                child.configure(text=UI_LANGUAGES[current_ui_language]['language_select'])
            # Update font frame
            elif any(x in child.cget('text') for x in ['Font', '폰트']):
                child.configure(text=UI_LANGUAGES[current_ui_language]['global_font'])
                # Update font frame labels
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Label):
                        if any(x in widget.cget('text') for x in ['Font', '폰트']):
                            widget.configure(text=UI_LANGUAGES[current_ui_language]['select_font'])
                        elif any(x in widget.cget('text') for x in ['Size', '크기']):
                            widget.configure(text=UI_LANGUAGES[current_ui_language]['select_size'])
                    elif isinstance(widget, tk.Button):
                        if any(x in widget.cget('text') for x in ['Reset', '초기화']):
                            widget.configure(text=UI_LANGUAGES[current_ui_language]['reset_font'])
            # Update color frame
            elif any(x in child.cget('text') for x in ['Color', '색상']):
                child.configure(text=UI_LANGUAGES[current_ui_language]['color_settings'])
                # Update color frame buttons
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Button):
                        if any(x in widget.cget('text') for x in ['Reset', '초기화']):
                            widget.configure(text=UI_LANGUAGES[current_ui_language]['reset_color'])
            # Update style frame
            elif any(x in child.cget('text') for x in ['Style', '스타일']):
                child.configure(text=UI_LANGUAGES[current_ui_language]['style_settings'])
                # Update style frame
                for frame in child.winfo_children():
                    if isinstance(frame, tk.Frame):
                        for center_frame in frame.winfo_children():
                            if isinstance(center_frame, tk.Frame):
                                for widget in center_frame.winfo_children():
                                    if isinstance(widget, tk.Label):
                                        if any(x in widget.cget('text') for x in ['Korean', '원문']):
                                            widget.configure(text=UI_LANGUAGES[current_ui_language]['korean_text'])
                                        elif any(x in widget.cget('text') for x in ['Translated', '번역문']):
                                            widget.configure(text=UI_LANGUAGES[current_ui_language]['translated_text'])
                                        elif any(x in widget.cget('text') for x in ['Reference', '참조문']):
                                            widget.configure(text=UI_LANGUAGES[current_ui_language]['reference_text'])
                                    elif isinstance(widget, tk.Button):
                                        if any(x in widget.cget('text') for x in ['Bold', '굵게']):
                                            widget.configure(text=UI_LANGUAGES[current_ui_language]['bold'])
                                        elif any(x in widget.cget('text') for x in ['Italic', '기울임']):
                                            widget.configure(text=UI_LANGUAGES[current_ui_language]['italic'])
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Button):
                        if any(x in widget.cget('text') for x in ['Reset', '초기화']):
                            widget.configure(text=UI_LANGUAGES[current_ui_language]['reset_style'])
    
    # Update color buttons
    for text_type, button in color_buttons.items():
        if text_type == 'korean':
            button.configure(text=UI_LANGUAGES[current_ui_language]['korean_text'])
        elif text_type == 'translation':
            button.configure(text=UI_LANGUAGES[current_ui_language]['translated_text'])
        elif text_type == 'reference':
            button.configure(text=UI_LANGUAGES[current_ui_language]['reference_text'])
    
    # Update style buttons
    for text_type in style_buttons:
        for button_type, button in style_buttons[text_type].items():
            if button_type == 'bold':
                button.configure(text=UI_LANGUAGES[current_ui_language]['bold'])
            elif button_type == 'italic':
                button.configure(text=UI_LANGUAGES[current_ui_language]['italic'])


def change_ui_language(new_language):
    global current_ui_language
    current_ui_language = new_language

    try:
        # Update Glossary Checker tab elements
        if 'version_frame' in globals() and version_frame.winfo_exists():
            for widget in version_frame.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(text=UI_LANGUAGES[current_ui_language]['platform_select'])
        
        # Update Glossary Checker buttons
        if 'new_term_list_button' in globals() and new_term_list_button.winfo_exists():
            new_term_list_button.config(text=UI_LANGUAGES[current_ui_language]['new_terms_glossary'])
        if 'consistency_check_button' in globals() and consistency_check_button.winfo_exists():
            consistency_check_button.config(text=UI_LANGUAGES[current_ui_language]['glossary_crosscheck'])

        # Update active dialog if it exists
        if 'active_dialog' in globals() and active_dialog and active_dialog.winfo_exists():
            # Update all frames in the dialog
            for widget in active_dialog.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.LabelFrame):
                            # Update frame labels
                            if "File Upload" in child['text'] or "파일 업로드" in child['text']:
                                child.config(text=UI_LANGUAGES[current_ui_language]['file_upload'])
                            elif "Glossary Base" in child['text'] or "글로서리 기준" in child['text']:
                                child.config(text=UI_LANGUAGES[current_ui_language]['glossary_base_selection'])
                            elif "Glossary Cross" in child['text'] or "통일성" in child['text']:
                                child.config(text=UI_LANGUAGES[current_ui_language]['glossary_crosscheck_selection'])
                            
                            # Update all radio buttons in the frame
                            for radio in child.winfo_children():
                                if isinstance(radio, tk.Radiobutton):
                                    if "Use Language" in radio['text'] or "렝귀지 데이터 사용" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['use_language_data'])
                                    elif "Use Close" in radio['text'] or "클로즈 데이터 사용" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['use_close_data'])
                                    elif "Use Both" in radio['text'] or "두 데이터 모두" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['use_both_combined'])
                                    elif "Check Language" in radio['text'] or "렝귀지 데이터 체크" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['check_language_data'])
                                    elif "Check Close" in radio['text'] or "클로즈 데이터 체크" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['check_close_data'])
                                    elif "Check Both" in radio['text'] or "두 데이터 모두 체크" in radio['text']:
                                        radio.config(text=UI_LANGUAGES[current_ui_language]['check_both_combined'])
                        
                        elif isinstance(child, tk.Button):
                            if "Start" in child['text'] or "시작" in child['text']:
                                child.config(text=UI_LANGUAGES[current_ui_language]['start_crosscheck'])
                            elif "Language Data" in child['text'] or "렝귀지 데이터" in child['text']:
                                if "Uploaded" in child['text'] or "업로드됨" in child['text']:
                                    child.config(text=UI_LANGUAGES[current_ui_language]['language_data_uploaded'])
                                else:
                                    child.config(text=UI_LANGUAGES[current_ui_language]['select_language_data'])
                            elif "Close Data" in child['text'] or "클로즈 데이터" in child['text']:
                                if "Uploaded" in child['text'] or "업로드됨" in child['text']:
                                    child.config(text=UI_LANGUAGES[current_ui_language]['close_data_uploaded'])
                                else:
                                    child.config(text=UI_LANGUAGES[current_ui_language]['select_close_data'])

    except Exception as e:
        print(f"Error updating UI: {str(e)}")

    # Update Quick Search tab buttons
    create_button.config(text=UI_LANGUAGES[current_ui_language]['create_dict'])
    load_button.config(text=UI_LANGUAGES[current_ui_language]['load_dict'])
    reference_button.config(text=UI_LANGUAGES[current_ui_language]['reference_off'])
    settings_button.config(text=UI_LANGUAGES[current_ui_language]['settings'])
    search_button.config(text=UI_LANGUAGES[current_ui_language]['search'])
    contains_radio.config(text=UI_LANGUAGES[current_ui_language]['contains'])
    exact_radio.config(text=UI_LANGUAGES[current_ui_language]['exact_match'])
    load_more_button.config(text=UI_LANGUAGES[current_ui_language]['load_more'])
    one_line_radio.config(text=UI_LANGUAGES[current_ui_language]['one_line'])
    multi_line_radio.config(text=UI_LANGUAGES[current_ui_language]['multi_line'])
    
    # Update settings window if it's open
    if settings_window_instance and settings_window_instance.winfo_exists():
        update_settings_window(settings_window_instance)

    # Update load button text if dictionary is loaded
    active_dict = dict_manager.get_active_dictionary()
    if active_dict:
        game, lang = active_dict
        load_button.config(
            text=UI_LANGUAGES[current_ui_language]['loaded_dict'].format(
                game=game, lang=lang
            )
        )
    
    # Update reference button text if reference is active
    if reference_active and dict_manager.reference_dict:
        game, lang = dict_manager.reference_dict
        reference_button.config(
            text=UI_LANGUAGES[current_ui_language]['reference_with_lang'].format(
                game=game, lang=lang
            )
        )
    
    # Save language preference
    font_settings['ui_language'] = current_ui_language
    save_settings()



def open_settings():
    global settings_window_instance
    
    if settings_window_instance is not None:
        if settings_window_instance.winfo_exists():
            settings_window_instance.lift()
            settings_window_instance.focus_force()
            return
        else:
            settings_window_instance = None
    
    settings_window = tk.Toplevel(window)
    settings_window.transient(window)  # This makes it stay on top of main window
    settings_window_instance = settings_window
    settings_window.title(UI_LANGUAGES[current_ui_language]['settings_title'])
    settings_window.geometry("400x600")
    center_dialog(settings_window, window)
    
    def update_style(text_type, style_type):
        current_style = font_settings['styles'][text_type]
        if style_type == 'bold':
            if 'bold' in current_style:
                current_style = current_style.replace('bold', '').strip()
                style_buttons[text_type]['bold'].config(bg='SystemButtonFace')
            else:
                current_style = f"bold {current_style}".strip()
                style_buttons[text_type]['bold'].config(bg='green')
        elif style_type == 'italic':
            if 'italic' in current_style:
                current_style = current_style.replace('italic', '').strip()
                style_buttons[text_type]['italic'].config(bg='SystemButtonFace')
            else:
                current_style = f"italic {current_style}".strip()
                style_buttons[text_type]['italic'].config(bg='green')
        
        font_settings['styles'][text_type] = current_style
        save_settings()
        update_text_display()
    
    def reset_section(section):
        if section == 'font':
            font_var.set('Arial')
            size_var.set('10')
            font_settings['family'] = 'Arial'
            font_settings['size'] = 10
        elif section == 'color':
            for text_type in ['korean', 'translation', 'reference']:
                font_settings['colors'][text_type] = '#000000'
                color_buttons[text_type].config(bg='#000000', fg='white')
        elif section == 'style':
            for text_type in ['korean', 'translation', 'reference']:
                font_settings['styles'][text_type] = ''
                style_buttons[text_type]['bold'].config(bg='SystemButtonFace')
                style_buttons[text_type]['italic'].config(bg='SystemButtonFace')
        save_settings()
        update_text_display()

    # Language Selection
    lang_frame = ttk.LabelFrame(settings_window, text=UI_LANGUAGES[current_ui_language]['language_select'])
    lang_frame.pack(pady=10, padx=10, fill="x")
    
    lang_var = tk.StringVar(value=current_ui_language)
    for lang in UI_LANGUAGES.keys():
        ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang,
                       command=lambda: change_ui_language(lang_var.get())).pack(anchor="w")
    
    # Font Settings
    font_frame = ttk.LabelFrame(settings_window, text=UI_LANGUAGES[current_ui_language]['global_font'])
    font_frame.pack(pady=10, padx=10, fill="x")
    
    font_var = tk.StringVar(value=font_settings['family'])
    tk.Label(font_frame, text=UI_LANGUAGES[current_ui_language]['select_font']).pack()
    font_combo = ttk.Combobox(font_frame, textvariable=font_var, values=sorted(font.families()))
    font_combo.pack(pady=5)
    
    size_var = tk.StringVar(value=str(font_settings['size']))
    tk.Label(font_frame, text=UI_LANGUAGES[current_ui_language]['select_size']).pack()
    size_combo = ttk.Combobox(font_frame, textvariable=size_var, values=[str(i) for i in range(8, 25)])
    size_combo.pack(pady=5)
    
    def on_setting_change(*args):
        font_settings['family'] = font_var.get()
        font_settings['size'] = int(size_var.get())
        save_settings()
        update_text_display()
    
    font_var.trace('w', on_setting_change)
    size_var.trace('w', on_setting_change)
    
    tk.Button(font_frame, text=UI_LANGUAGES[current_ui_language]['reset_font'], 
              command=lambda: reset_section('font')).pack(pady=5)
    
    # Color Settings
    color_frame = ttk.LabelFrame(settings_window, text=UI_LANGUAGES[current_ui_language]['color_settings'])
    color_frame.pack(pady=10, padx=10, fill="x")
    
    global color_buttons
    color_buttons = {}
    color_labels = {'korean': 'korean_text', 'translation': 'translated_text', 'reference': 'reference_text'}
    
    for text_type in ['korean', 'translation', 'reference']:
        color = font_settings['colors'][text_type]
        r, g, b = tuple(int(color[1:][i:i+2], 16) for i in (0, 2, 4))
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = 'white' if brightness < 128 else 'black'
        btn = tk.Button(color_frame, 
                     text=UI_LANGUAGES[current_ui_language][color_labels[text_type]],
                     command=lambda t=text_type: choose_color(t),
                     bg=color,
                     fg=text_color)
        btn.pack(pady=5)
        color_buttons[text_type] = btn
    
    tk.Button(color_frame, text=UI_LANGUAGES[current_ui_language]['reset_color'], 
              command=lambda: reset_section('color')).pack(pady=5)
    
    # Style Settings
    style_frame = ttk.LabelFrame(settings_window, text=UI_LANGUAGES[current_ui_language]['style_settings'])
    style_frame.pack(pady=10, padx=10, fill="x")
    
    global style_buttons
    style_buttons = {}
    
    for text_type in ['korean', 'translation', 'reference']:
        style_buttons[text_type] = {}
        
        type_frame = tk.Frame(style_frame)
        type_frame.pack(pady=5, fill='x')
        
        center_frame = tk.Frame(type_frame)
        center_frame.pack(expand=True)
        
        tk.Label(center_frame, 
                text=UI_LANGUAGES[current_ui_language][color_labels[text_type]]).pack(side='left', padx=5)
        
        bold_btn = tk.Button(center_frame, text=UI_LANGUAGES[current_ui_language]['bold'], width=6,
                            command=lambda t=text_type: update_style(t, 'bold'))
        bold_btn.pack(side='left', padx=2)
        style_buttons[text_type]['bold'] = bold_btn
        
        italic_btn = tk.Button(center_frame, text=UI_LANGUAGES[current_ui_language]['italic'], width=6,
                           command=lambda t=text_type: update_style(t, 'italic'))
        italic_btn.pack(side='left', padx=2)
        style_buttons[text_type]['italic'] = italic_btn
        
        if 'bold' in font_settings['styles'][text_type]:
            bold_btn.config(bg='green')
        if 'italic' in font_settings['styles'][text_type]:
            italic_btn.config(bg='green')
    
    tk.Button(style_frame, text=UI_LANGUAGES[current_ui_language]['reset_style'], 
              command=lambda: reset_section('style')).pack(pady=5)
              
    def on_closing():
        global settings_window_instance
        settings_window_instance = None
        settings_window.destroy()
    
    settings_window.protocol("WM_DELETE_WINDOW", on_closing)


class DictionaryManager:
    def __init__(self):
        self.active_game = None
        self.active_language = None
        self.reference_dict = None
        self.dictionaries = {}
        self.load_available_dictionaries()

    def load_available_dictionaries(self):
        """Scan for existing dictionaries and populate the dictionaries dict"""
        for game in GAMES:
            self.dictionaries[game] = {}
            for lang in LANGUAGES:
                dict_path = os.path.join(game, lang)
                if os.path.exists(dict_path):
                    if os.path.exists(os.path.join(dict_path, 'dictionary.pkl')):
                        self.dictionaries[game][lang] = {
                            'path': dict_path,
                            'active': False
                        }

    def create_dictionary(self, game, language, source_file):
        """Create a new dictionary for the specified game and language"""
        dict_path = os.path.join(game, language)
        os.makedirs(dict_path, exist_ok=True)
        
        # Process the dictionary data
        split_dict, whole_dict = process_data(source_file, progress_var)
        
        if split_dict and whole_dict:
            # Save the dictionaries
            dictionary_data = {
                'split_dict': split_dict,
                'whole_dict': whole_dict,
                'string_keys': string_keys,
                'creation_date': time.strftime("%m/%d %H:%M")
            }
            with open(os.path.join(dict_path, 'dictionary.pkl'), 'wb') as f:
                pickle.dump(dictionary_data, f)
            
            # Update the dictionaries registry
            if game not in self.dictionaries:
                self.dictionaries[game] = {}
            self.dictionaries[game][language] = {
                'path': dict_path,
                'active': False
            }
            return True
        return False

    def load_dictionary(self, game, language):
            """Load a dictionary into memory"""
            global split_dict, whole_dict, string_keys
            
            dict_path = os.path.join(game, language)
            if os.path.exists(dict_path):
                try:
                    with open(os.path.join(dict_path, 'dictionary.pkl'), 'rb') as f:
                        data = pickle.load(f)
                        split_dict = data['split_dict']
                        whole_dict = data['whole_dict']
                        string_keys = data.get('string_keys', {})
                        creation_date = data.get('creation_date', 'N/A')
                    
                    # Update active status
                    self.active_game = game
                    self.active_language = language
                    self.update_active_status(game, language)
                    
                    # Update load button text with creation date
                    load_button.config(
                        text=UI_LANGUAGES[current_ui_language]['loaded_dict'].format(
                            game=game, lang=language
                        ) + f" ({creation_date})",
                        bg="green"
                    )
                    return True
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load dictionary: {str(e)}")
            return False

    def update_active_status(self, game, language):
        """Update the active status of dictionaries"""
        for g in self.dictionaries:
            for l in self.dictionaries.get(g, {}):
                self.dictionaries[g][l]['active'] = (g == game and l == language)

    def get_active_dictionary(self):
        """Get the currently active dictionary info"""
        if self.active_game and self.active_language:
            return (self.active_game, self.active_language)
        return None

    def set_reference_dictionary(self, game, language):
        """Set a dictionary as reference"""
        global ref_split_dict, ref_whole_dict
        
        dict_path = os.path.join(game, language)
        if os.path.exists(dict_path):
            try:
                with open(os.path.join(dict_path, 'dictionary.pkl'), 'rb') as f:
                    data = pickle.load(f)
                    ref_split_dict = data['split_dict']
                    ref_whole_dict = data['whole_dict']
                self.reference_dict = (game, language)
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load reference dictionary: {str(e)}")
        return False

# Initialize the dictionary manager
dict_manager = DictionaryManager()


def process_data(filepath, progress_var):
    split_dict = {}
    whole_dict = {}
    global string_keys
    string_keys = {}  # Reset string keys
    
    try:
        # Show progress bar at start
        show_progress()
        
        progress_var.set("Loading data file...")
        progress_bar['value'] = 5
        window.update_idletasks()
        
        # Modified: Tell pandas to ignore quotes entirely when parsing
        df = pd.read_csv(filepath, delimiter="\t", header=None, usecols=range(7), 
                        dtype=str, quoting=csv.QUOTE_NONE, 
                        quotechar=None, escapechar=None)
        
        total_rows = len(df)

        # Main processing (10-70%)
        korean_lines_split = []
        french_lines_split = []
        korean_lines_whole = []
        french_lines_whole = []
        string_keys_split = []  # Modified: Store full key tuple
        string_keys_whole = []  # Modified: Store full key tuple

        last_update = time.time()
        update_interval = 0.5

        for row_index, row in df.iterrows():
            current_time = time.time()
            if current_time - last_update >= update_interval:
                progress = (row_index + 1) / total_rows * 60
                progress_var.set(f"Processing language data: {(progress * 100 / 60):.1f}% complete")
                progress_bar['value'] = 10 + progress
                window.update_idletasks()
                last_update = current_time

            korean_text = row[5]
            french_text = row[6]
            # Modified: Create full string key tuple
            str_key = tuple(str(x).strip() if x is not None else '' for x in row[0:5])

            if pd.isna(korean_text) or pd.isna(french_text):
                continue

            korean_text = normalize_dictionary_text(korean_text)
            french_text = normalize_dictionary_text(french_text)

            korean_tokens = tokenize(korean_text)
            french_tokens = tokenize(french_text)

            if len(korean_tokens) == len(french_tokens) and korean_tokens:
                for kr, fr in zip(korean_tokens, french_tokens):
                    korean_lines_split.append(kr)
                    french_lines_split.append(fr)
                    # Modified: Store full key tuple with each split line
                    string_keys_split.append((kr, str_key))
            else:
                if korean_text and french_text and '\t' not in korean_text and '\t' not in french_text:
                    korean_lines_whole.append(korean_text)
                    french_lines_whole.append(french_text)
                    # Modified: Store full key tuple with whole text
                    string_keys_whole.append((korean_text, str_key))

        # Creating dictionaries (70-95%)
        progress_var.set("Creating dictionaries...")
        progress_bar['value'] = 70
        window.update_idletasks()
        
        # Modified: Create dictionary while preserving all entries
        for kr, fr, key_data in zip(korean_lines_split, french_lines_split, string_keys_split):
            if kr not in split_dict:
                split_dict[kr] = []
            split_dict[kr].append((fr, key_data[1]))  # Store translation with its key

        for kr, fr, key_data in zip(korean_lines_whole, french_lines_whole, string_keys_whole):
            if kr not in whole_dict:
                whole_dict[kr] = []
            whole_dict[kr].append((fr, key_data[1]))  # Store translation with its key

        progress_var.set("Dictionary creation complete!")
        progress_bar['value'] = 100
        window.update_idletasks()
        
        window.after(1000, hide_progress)
        return split_dict, whole_dict

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during processing: {str(e)}")
        progress_var.set("Error occurred during processing")
        progress_bar['value'] = 0
        hide_progress()
        return {}, {}

def search_one_line(query, match_type="contains", start_index=0, limit=50):
    if not query or query.isspace():
        return []
    
    try:
        results = []
        query_lower = query.lower()
        
        def check_match(text1, text2):
            if match_type == "contains":
                return query_lower in text1.lower() or query_lower in text2.lower()
            return query_lower == text1.lower() or query_lower == text2.lower()

        # Helper to validate string key and content
        def is_valid_entry(kr, fr, key):
            # Check if any key component is empty
            if any(not str(k).strip() for k in key):
                return False
            # Check if content is empty
            if not kr.strip() or not fr.strip():
                return False
            return True
        
        # Search in main dictionary (KR-FR)
        for kr, translations in split_dict.items():
            for fr, key in translations:
                if check_match(str(kr), str(fr)) and is_valid_entry(kr, fr, key):
                    if reference_active and dict_manager.reference_dict:
                        ref_fr = None
                        if kr in ref_split_dict and ref_split_dict[kr]:
                            ref_fr = ref_split_dict[kr][0][0]
                        elif kr in ref_whole_dict and ref_whole_dict[kr]:
                            ref_fr = ref_whole_dict[kr][0][0]
                        results.append((kr, fr, ref_fr, key))
                    else:
                        results.append((kr, fr, key))
                
        for kr, translations in whole_dict.items():
            for fr, key in translations:
                if check_match(str(kr), str(fr)) and is_valid_entry(kr, fr, key):
                    if reference_active and dict_manager.reference_dict:
                        ref_fr = None
                        if kr in ref_split_dict and ref_split_dict[kr]:
                            ref_fr = ref_split_dict[kr][0][0]
                        elif kr in ref_whole_dict and ref_whole_dict[kr]:
                            ref_fr = ref_whole_dict[kr][0][0]
                        results.append((kr, fr, ref_fr, key))
                    else:
                        results.append((kr, fr, key))
        
        # Search in reference dictionary if active (EN)
        if reference_active and dict_manager.reference_dict:
            for kr, ref_translations in ref_split_dict.items():
                for ref_fr, _ in ref_translations:
                    if query_lower in str(ref_fr).lower():
                        fr = None
                        key = None
                        if kr in split_dict and split_dict[kr]:
                            fr, key = split_dict[kr][0]
                            if is_valid_entry(kr, fr, key):
                                results.append((kr, fr, ref_fr, key))
                        elif kr in whole_dict and whole_dict[kr]:
                            fr, key = whole_dict[kr][0]
                            if is_valid_entry(kr, fr, key):
                                results.append((kr, fr, ref_fr, key))
            
            for kr, ref_translations in ref_whole_dict.items():
                for ref_fr, _ in ref_translations:
                    if query_lower in str(ref_fr).lower():
                        fr = None
                        key = None
                        if kr in split_dict and split_dict[kr]:
                            fr, key = split_dict[kr][0]
                            if is_valid_entry(kr, fr, key):
                                results.append((kr, fr, ref_fr, key))
                        elif kr in whole_dict and whole_dict[kr]:
                            fr, key = whole_dict[kr][0]
                            if is_valid_entry(kr, fr, key):
                                results.append((kr, fr, ref_fr, key))
        
        # Sort results by Korean text length
        results.sort(key=lambda x: len(str(x[0])))
        
        # Add a safety check for the slicing
        if start_index >= len(results):
            return []
            
        return results[start_index:start_index + limit]
        
    except Exception as e:
        print(f"Error in search_one_line: {str(e)}")
        return []

def search_multi_line(query, match_type="contains", start_index=0, limit=50):
    if not query or query.isspace():
        return ([], [], []) if reference_active else ([], [])
        
    queries = [q.strip() for q in query.split('\n') if q.strip()]
    french_results = []
    korean_results = []
    ref_french_results = []

    def is_valid_entry(kr, fr, key):
        # Check if any key component is empty
        if any(not str(k).strip() for k in key):
            return False
        # Check if content is empty
        if not kr.strip() or not fr.strip():
            return False
        return True

    for q in queries:
        results = search_one_line(q, match_type, 0, 1)
        if results:
            if reference_active:
                kr, fr, ref_fr, key = results[0]
                if is_valid_entry(kr, fr, key):
                    french_results.append(fr)
                    korean_results.append(kr)
                    ref_french_results.append(ref_fr if ref_fr else "❓❓")
                else:
                    french_results.append("❓❓")
                    korean_results.append("❓❓")
                    ref_french_results.append("❓❓")
            else:
                kr, fr, key = results[0]
                if is_valid_entry(kr, fr, key):
                    french_results.append(fr)
                    korean_results.append(kr)
                else:
                    french_results.append("❓❓")
                    korean_results.append("❓❓")
        else:
            french_results.append("❓❓")
            korean_results.append("❓❓")
            if reference_active:
                ref_french_results.append("❓❓")

    if reference_active:
        return (french_results, korean_results, ref_french_results)
    return (french_results, korean_results)


def update_text_display():
    """Updated update_text_display function with proper style handling"""
    current_pos = result_text.yview()
    content = result_text.get(1.0, tk.END)
    result_text.delete(1.0, tk.END)
    
    results = content.split('\n\n')
    
    for i, result in enumerate(results):
        if not result.strip():
            continue
            
        lines = result.strip().split('\n')
        if not lines:
            continue
            
        kr_tag = f"korean_{i}"
        tr_tag = f"translation_{i}"
        ref_tag = f"reference_{i}"
        
        result_text.tag_configure(kr_tag, 
            font=(font_settings['family'], font_settings['size'], font_settings['styles']['korean']),
            foreground=font_settings['colors']['korean'])
        result_text.tag_configure(tr_tag, 
            font=(font_settings['family'], font_settings['size'], font_settings['styles']['translation']),
            foreground=font_settings['colors']['translation'])
        result_text.tag_configure(ref_tag, 
            font=(font_settings['family'], font_settings['size'], font_settings['styles']['reference']),
            foreground=font_settings['colors']['reference'])
        
        # Insert Korean text (first line)
        start_pos = result_text.index("end-1c")
        result_text.insert(tk.END, post_process_newlines(lines[0]) + '\n')
        end_pos = result_text.index("end-1c")
        result_text.tag_add(kr_tag, start_pos, end_pos)
        
        # Insert Translation text
        if len(lines) > 1:
            translation_lines = lines[1:-1] if reference_active and len(lines) > 2 else lines[1:]
            if translation_lines:
                start_pos = result_text.index("end-1c")
                result_text.insert(tk.END, '\n'.join(post_process_newlines(line) for line in translation_lines) + '\n')
                end_pos = result_text.index("end-1c")
                result_text.tag_add(tr_tag, start_pos, end_pos)
        
        # Insert Reference text if present
        if reference_active and len(lines) > 2:
            start_pos = result_text.index("end-1c")
            result_text.insert(tk.END, post_process_newlines(lines[-1]) + '\n')
            end_pos = result_text.index("end-1c")
            result_text.tag_add(ref_tag, start_pos, end_pos)
        
        # Add separation between results
        result_text.insert(tk.END, '\n')
    
    result_text.yview_moveto(current_pos[0])
    
    
    
def create_dictionary_dialog():
    dialog = tk.Toplevel(window)
    dialog.title("Create New Dictionary")
    dialog.geometry("300x600")
    dialog.transient(window)
    dialog.grab_set()
    center_dialog(dialog, window)
    
    # Game selection
    game_frame = ttk.LabelFrame(dialog, text="Select Game")
    game_frame.pack(padx=10, pady=5, fill="x")
    
    game_var = tk.StringVar()
    lang_var = tk.StringVar()

    games = GAMES
    for game in games:
        ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")
    
    # Language selection
    lang_frame = ttk.LabelFrame(dialog, text="Select Language")
    lang_frame.pack(padx=10, pady=5, fill="x")
    
    for lang in LANGUAGES:
        ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")
    
    def on_create():
        game = game_var.get()
        language = lang_var.get()
        
        if not game or not language:
            messagebox.showwarning("Warning", "Please select both game and language")
            return
            
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not filepath:
            return
            
        dialog.destroy()  # Close dialog before starting process
        progress_var.set(f"Creating {game} {language} dictionary...")
        
        def process():
            try:
                progress_var.set("Starting dictionary creation...")
                window.update_idletasks()

                if dict_manager.create_dictionary(game, language, filepath):
                    progress_var.set(f"{game} {language} dictionary created successfully.")
                    update_dictionary_buttons()
                else:
                    progress_var.set("Dictionary creation failed.")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create dictionary: {str(e)}")
                traceback.print_exc()
        
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
    
    create_btn = tk.Button(dialog, text="Create", command=on_create,
                          relief="raised",
                          bd=3,
                          padx=20,
                          pady=5,
                          font=('Helvetica', 10, 'bold'))
    create_btn.pack(pady=10)

def load_dictionary_dialog():
    dialog = tk.Toplevel(window)
    dialog.title("Load Dictionary")
    dialog.geometry("300x500")
    dialog.transient(window)
    dialog.grab_set()
    center_dialog(dialog, window)
    
    # Game selection
    game_frame = ttk.LabelFrame(dialog, text="Select Game")
    game_frame.pack(padx=10, pady=5, fill="x")
    
    game_var = tk.StringVar()
    lang_var = tk.StringVar()

    def update_languages(*args):
        for widget in lang_frame.winfo_children():
            widget.destroy()
        
        game = game_var.get()
        if game in dict_manager.dictionaries:
            for lang in dict_manager.dictionaries[game]:
                ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")
    
    for game in dict_manager.dictionaries:
        if dict_manager.dictionaries[game]:  # Only show games with dictionaries
            ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")
    
    # Language selection
    lang_frame = ttk.LabelFrame(dialog, text="Select Language")
    lang_frame.pack(padx=10, pady=5, fill="x")
    
    game_var.trace('w', update_languages)
    
    def on_load():
        game = game_var.get()
        language = lang_var.get()
        
        if not game or not language:
            messagebox.showwarning("Warning", "Please select both game and language")
            return
            
        dialog.destroy()
        if dict_manager.load_dictionary(game, language):
            reference_button.config(state=tk.NORMAL)
            update_dictionary_buttons()
    
    load_btn = tk.Button(dialog, text="Load", command=on_load,
                         relief="raised",
                         bd=3,
                         padx=20,
                         pady=5,
                         font=('Helvetica', 10, 'bold'))
    load_btn.pack(pady=10)

def set_reference_dialog():
    if not dict_manager.get_active_dictionary():
        messagebox.showwarning("Warning", "Please load a main dictionary first")
        return
        
    dialog = tk.Toplevel(window)
    dialog.title("Set Reference Dictionary")
    dialog.geometry("300x500")
    dialog.transient(window)
    dialog.grab_set()
    center_dialog(dialog, window)
    
    active_game, active_lang = dict_manager.get_active_dictionary()
    
    # Game selection
    game_frame = ttk.LabelFrame(dialog, text="Select Game")
    game_frame.pack(padx=10, pady=5, fill="x")
    
    game_var = tk.StringVar(value=active_game)  # Default to active game
    lang_var = tk.StringVar()
    
    def update_languages(*args):
        for widget in lang_frame.winfo_children():
            widget.destroy()
        
        game = game_var.get()
        if game in dict_manager.dictionaries:
            for lang in dict_manager.dictionaries[game]:
                if not (game == active_game and lang == active_lang):  # Don't show active dictionary
                    ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")
    
    for game in dict_manager.dictionaries:
        if dict_manager.dictionaries[game]:
            ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")
    
    # Language selection
    lang_frame = ttk.LabelFrame(dialog, text="Select Language")
    lang_frame.pack(padx=10, pady=5, fill="x")
    
    game_var.trace('w', update_languages)
    update_languages()  # Initial population
    
    def on_set():
        game = game_var.get()
        language = lang_var.get()
        
        if not game or not language:
            messagebox.showwarning("Warning", "Please select both game and language")
            return
        
        dialog.destroy()  # Close dialog before setting reference
        global reference_active
        if dict_manager.set_reference_dictionary(game, language):
            reference_active = True
            reference_button.config(
                text=UI_LANGUAGES[current_ui_language]['reference_with_lang'].format(
                    game=game, lang=language
                ), 
                bg="green"
            )
            
            # Refresh search results if any
            if 'search_query' in globals():
                on_search_click()
    
    set_ref_btn = tk.Button(dialog, text="Set Reference", command=on_set,
                           relief="raised",
                           bd=3,
                           padx=20,
                           pady=5,
                           font=('Helvetica', 10, 'bold'))
    set_ref_btn.pack(pady=10)

def toggle_reference():
    global reference_active, ref_split_dict, ref_whole_dict

    if not dict_manager.get_active_dictionary():
        messagebox.showwarning("Warning", "Please load a main dictionary first")
        return

    if not reference_active:
        set_reference_dialog()
    else:
        reference_active = False
        dict_manager.reference_dict = None
        reference_button.config(text=UI_LANGUAGES[current_ui_language]['reference_off'], bg="grey")
        
        # Clear the reference dictionaries
        ref_split_dict = {}
        ref_whole_dict = {}
        
        # Refresh search results if any
        if 'search_query' in globals():
            on_search_click()


def update_dictionary_buttons():
    # Update status in main window (e.g., in a status bar or label)
    active_dict = dict_manager.get_active_dictionary()
    if active_dict:
        game, lang = active_dict

        
def on_search_click(event=None):
    global search_query, search_match_type, search_start_index, selected_cells, last_selected_cell

    search_query = (one_line_search_entry.get().strip()
                    if search_type_var.get() == "one_line"
                    else multi_line_search_entry.get("1.0", tk.END).strip())

    if not search_query or search_query.isspace():
        return

    search_match_type = match_type_var.get()
    search_start_index = 0  # Reset the start index for new searches

    # Reset selections
    clear_selection()
    last_selected_cell = None

    # Clear existing results
    for widget in result_container.winfo_children():
        widget.destroy()

    try:
        display_results(50)
        # Re-enable load more button for new searches
        if search_type_var.get() == "one_line":
            load_more_button.config(state=tk.NORMAL)
    except Exception as e:
        messagebox.showerror("Error", f"Search error: {str(e)}")
        traceback.print_exc()






def normalize_display_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return text
        
    # Remove technical codes while preserving structure
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)  # Remove scale tags
    text = re.sub(r'<color[^>]*>|</color>', '', text)  # Remove color tags
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)  # Remove PA color tags
    text = re.sub(r'\{AudioVoice[^}]*\}', '', text)  # Remove AudioVoice codes
    text = re.sub(r'\{ChangeScene[^}]*\}', '', text)  # Remove ChangeScene codes  
    text = re.sub(r'\{ChangeAction[^}]*\}', '', text)  # Remove ChangeAction codes
    return text.strip()




# Update the create_cell function
def create_cell(parent, content, style_type, wraplength, row_index=None, col_index=None):
    frame = tk.Frame(parent, relief="solid", borderwidth=1)
    
    # Apply normalization if enabled
    display_content = normalize_display_text(content) if normalize_display_var.get() else content
    
    label = tk.Label(frame,
                     text=post_process_newlines(display_content),
                     wraplength=wraplength,
                     font=(font_settings['family'], font_settings['size'],
                           font_settings['styles'][style_type]),
                     fg=font_settings['colors'][style_type],
                     padx=5,
                     pady=5,
                     justify=tk.LEFT,
                     anchor='w',
                     bg='white')
    label.pack(fill=tk.BOTH, expand=True)
    
    frame.row_index = row_index
    frame.col_index = col_index
    frame.is_editing = False
    
    def start_editing(event):
        if frame.is_editing:
            return
        
        frame.is_editing = True
        label.pack_forget()
        
        editor = tk.Text(frame,
                        font=(font_settings['family'], font_settings['size'], 
                              font_settings['styles'][style_type]),
                        fg=font_settings['colors'][style_type],
                        wrap=tk.WORD,
                        height=5)
        editor.insert('1.0', content)
        editor.pack(fill=tk.BOTH, expand=True)
        editor.focus_set()
        
        # Enable text selection in editor
        editor.tag_configure("sel", background="#0a246a", foreground="white")
        
        def save_changes(event=None):
            try:
                # Try to get selected text first
                selected_text = editor.selection_get()
                pyperclip.copy(selected_text)
            except tk.TclError:
                pass
            editor.destroy()
            label.pack(fill=tk.BOTH, expand=True)
            frame.is_editing = False
            return "break"
            
        def cancel_editing(event=None):
            editor.destroy()
            label.pack(fill=tk.BOTH, expand=True)
            frame.is_editing = False
            
        editor.bind('<Control-c>', lambda e: None)  # Allow default copy behavior
        editor.bind('<Escape>', cancel_editing)
        editor.bind('<FocusOut>', save_changes)
    
    label.bind('<Double-Button-1>', start_editing)
    
    def on_enter(event):
        if frame not in selected_cells:
            label.configure(bg='#e0e0e0')

    def on_leave(event):
        if frame not in selected_cells:
            label.configure(bg='white')

    def on_click(event):
        global last_selected_cell
        if event.state & 0x0004:  # Ctrl key is pressed
            toggle_selection(frame)
            last_selected_cell = frame
        elif event.state & 0x0001:  # Shift key is pressed
            if last_selected_cell:
                select_range(last_selected_cell, frame)
            else:
                add_to_selection(frame)
                last_selected_cell = frame
        else:
            clear_selection()
            add_to_selection(frame)
            last_selected_cell = frame

    label.bind("<Enter>", on_enter)
    label.bind("<Leave>", on_leave)
    label.bind("<Button-1>", on_click)
    
    return frame


# Define helper functions for cell selection
def toggle_selection(frame):
    label = frame.winfo_children()[0]  # Get the label widget
    if frame in selected_cells:
        label.configure(bg='white')
        selected_cells.remove(frame)
    else:
        label.configure(bg='#a0a0ff')
        selected_cells.add(frame)

def add_to_selection(frame):
    label = frame.winfo_children()[0]  # Get the label widget
    label.configure(bg='#a0a0ff')
    selected_cells.add(frame)

def clear_selection():
    for frame in selected_cells:
        try:
            label = frame.winfo_children()[0]  # Get the label widget
            label.configure(bg='white')
        except tk.TclError:
            pass
    selected_cells.clear()

def select_range(start_label, end_label):
    if not start_label or not end_label:
        return
    # Get the start and end positions
    start_row, start_col = start_label.row_index, start_label.col_index
    end_row, end_col = end_label.row_index, end_label.col_index

    # Determine the range
    min_row, max_row = sorted((start_row, end_row))
    min_col, max_col = sorted((start_col, end_col))

    # Clear previous selection
    clear_selection()

    # Select all cells in the range
    for child in result_container.winfo_children():
        if hasattr(child, 'row_index') and hasattr(child, 'col_index'):
            if min_row <= child.row_index <= max_row and min_col <= child.col_index <= max_col:
                add_to_selection(child)


# Update the display_results function
def display_results(count, append=False):
    global search_query, search_match_type, search_start_index
    try:
        if not append:
            # Clear existing content in result_container
            for widget in result_container.winfo_children():
                widget.destroy()

            # Clear selections
            clear_selection()
            global last_selected_cell
            last_selected_cell = None

            # Reset row index offset
            row_index_offset = 0
        else:
            # Calculate the current number of rows to set the offset more safely
            existing_rows = len([w for w in result_container.winfo_children() 
                               if hasattr(w, 'row_index')])
            row_index_offset = existing_rows

        # Configure grid columns for stretching
        result_container.update_idletasks()
        total_width = result_container.winfo_width()
        
        # Set number of columns based on display mode
        columns = 3 if show_string_key else 2
        if reference_active:
            columns += 1  # Add one more column for reference translation
        wraplength = total_width // columns - 20
        
        # Configure columns with equal weight
        for i in range(columns):
            result_container.grid_columnconfigure(i, weight=1)

        if search_type_var.get() == "one_line":
            results = search_one_line(search_query, search_match_type, search_start_index, count)
            
            if not results:  # No more results
                load_more_button.config(state=tk.DISABLED)
                return

            for idx, result in enumerate(results):
                display_idx = idx + row_index_offset
                
                if reference_active:
                    korean, french, ref_french, key = result
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        key_content = ' '.join(str(k) for k in key)
                        key_cell = create_cell(result_container, key_content, 'korean', wraplength, display_idx, 0)
                        key_cell.grid(row=display_idx, column=0, sticky='nsew', padx=1, pady=1)

                    kr_cell = create_cell(result_container, korean, 'korean', wraplength, display_idx, col_offset)
                    fr_cell = create_cell(result_container, french, 'translation', wraplength, display_idx, col_offset + 1)
                    ref_cell = create_cell(result_container, ref_french if ref_french else "❓❓", 'reference', 
                                         wraplength, display_idx, col_offset + 2)

                    kr_cell.grid(row=display_idx, column=col_offset, sticky='nsew', padx=1, pady=1)
                    fr_cell.grid(row=display_idx, column=col_offset + 1, sticky='nsew', padx=1, pady=1)
                    ref_cell.grid(row=display_idx, column=col_offset + 2, sticky='nsew', padx=1, pady=1)
                else:
                    korean, french, key = result
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        key_content = ' '.join(str(k) for k in key)
                        key_cell = create_cell(result_container, key_content, 'korean', wraplength, display_idx, 0)
                        key_cell.grid(row=display_idx, column=0, sticky='nsew', padx=1, pady=1)

                    kr_cell = create_cell(result_container, korean, 'korean', wraplength, display_idx, col_offset)
                    fr_cell = create_cell(result_container, french, 'translation', wraplength, display_idx, col_offset + 1)

                    kr_cell.grid(row=display_idx, column=col_offset, sticky='nsew', padx=1, pady=1)
                    fr_cell.grid(row=display_idx, column=col_offset + 1, sticky='nsew', padx=1, pady=1)

                # Configure row for proper stretching
                result_container.grid_rowconfigure(display_idx, weight=0)

        elif search_type_var.get() == "multi_line":
            if reference_active:
                french_results, korean_results, ref_french_results = search_multi_line(
                    search_query, search_match_type, search_start_index, count)
                
                for idx, (kr, fr, ref_fr) in enumerate(zip(korean_results, french_results, ref_french_results)):
                    display_idx = idx + row_index_offset
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        # For multi-line, use the key from search results if available
                        key_results = search_one_line(kr, "exact", 0, 1)
                        key = key_results[0][3] if key_results else tuple()
                        key_content = ' '.join(str(k) for k in key)
                        key_cell = create_cell(result_container, key_content, 'korean', wraplength, display_idx, 0)
                        key_cell.grid(row=display_idx, column=0, sticky='nsew', padx=1, pady=1)

                    kr_cell = create_cell(result_container, kr, 'korean', wraplength, display_idx, col_offset)
                    fr_cell = create_cell(result_container, fr, 'translation', wraplength, display_idx, col_offset + 1)
                    ref_cell = create_cell(result_container, ref_fr, 'reference', wraplength, display_idx, col_offset + 2)

                    kr_cell.grid(row=display_idx, column=col_offset, sticky='nsew', padx=1, pady=1)
                    fr_cell.grid(row=display_idx, column=col_offset + 1, sticky='nsew', padx=1, pady=1)
                    ref_cell.grid(row=display_idx, column=col_offset + 2, sticky='nsew', padx=1, pady=1)

                    result_container.grid_rowconfigure(display_idx, weight=0)
            else:
                french_results, korean_results = search_multi_line(
                    search_query, search_match_type, search_start_index, count)
                
                for idx, (kr, fr) in enumerate(zip(korean_results, french_results)):
                    display_idx = idx + row_index_offset
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        # For multi-line, use the key from search results if available
                        key_results = search_one_line(kr, "exact", 0, 1)
                        key = key_results[0][2] if key_results else tuple()
                        key_content = ' '.join(str(k) for k in key)
                        key_cell = create_cell(result_container, key_content, 'korean', wraplength, display_idx, 0)
                        key_cell.grid(row=display_idx, column=0, sticky='nsew', padx=1, pady=1)

                    kr_cell = create_cell(result_container, kr, 'korean', wraplength, display_idx, col_offset)
                    fr_cell = create_cell(result_container, fr, 'translation', wraplength, display_idx, col_offset + 1)

                    kr_cell.grid(row=display_idx, column=col_offset, sticky='nsew', padx=1, pady=1)
                    fr_cell.grid(row=display_idx, column=col_offset + 1, sticky='nsew', padx=1, pady=1)

                    result_container.grid_rowconfigure(display_idx, weight=0)

    except Exception as e:
        print(f"Error in display_results: {str(e)}")
        traceback.print_exc()

    # Force update of display
    result_container.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    window.after(100, lambda: result_container.update_idletasks())
    
    


# Update the copy_selected_cells function
def on_copy(event=None):
    if selected_cells:
        # Copy selected cells
        copied_text = ''
        # Sort selected cells by their position
        sorted_cells = sorted(selected_cells, key=lambda c: (c.row_index, c.col_index))
        current_row = None
        row_text = []
        for frame in sorted_cells:
            if frame.row_index != current_row:
                if row_text:
                    copied_text += '\t'.join(row_text) + '\n'
                    row_text = []
                current_row = frame.row_index
            # Get the label from the frame (first child)
            label = frame.winfo_children()[0]
            cell_text = label.cget('text').replace("❓❓", "")
            row_text.append(cell_text)
        if row_text:
            copied_text += '\t'.join(row_text) + '\n'
        pyperclip.copy(copied_text.strip())
        return "break"
    else:
        # Copy selected text from widget
        try:
            widget = event.widget
            selection = widget.selection_get()
            clipboard_text = selection.replace("❓❓", "")
            pyperclip.copy(clipboard_text)
            return "break"
        except tk.TclError:
            pass


def load_more_results():
    global search_start_index
    try:
        current_query = search_query if 'search_query' in globals() else None
        if not current_query:
            return

        # Store current result count
        previous_count = len([w for w in result_container.winfo_children() if hasattr(w, 'row_index')])
        
        # Save current scroll position
        current_scroll = canvas.yview()[0]
            
        # Only increment if we're not already at the limit
        results = search_one_line(search_query, search_match_type, search_start_index + 50, 50)
        if not results:
            # We've hit the limit - disable button and stop
            load_more_button.config(state=tk.DISABLED)
            return
            
        # If we got here, there are more results, so increment and display
        search_start_index += 50
        display_results(50, append=True)
        
        # Update canvas and restore scroll
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.yview_moveto(current_scroll)
            
    except Exception as e:
        print(f"Error in load_more_results: {str(e)}")
        # Don't show error to user, just stabilize the state
        search_start_index = max(0, search_start_index - 50)  # Revert if needed
        load_more_button.config(state=tk.DISABLED)



def on_mousewheel(event):
    canvas.yview_scroll(-1 * (event.delta // 120), "units")



def glossary_checker_tab(parent):
    global new_term_list_button, consistency_check_button, version_frame, version_label, active_dialog
    active_dialog = None
    
    def tokenize(text):
        if isinstance(text, str) and text.strip() != '' and '\t' not in text:
            return re.split(r'\\?\\n|\n', text)
        else:
            return []

    def process_data(filepath, progress_var):
        whole_dict = {}
        try:
            df = pd.read_csv(filepath, delimiter="\t", header=None, usecols=[5, 6], dtype=str)
            total_rows = len(df)

            for row_index, (korean_text, french_text) in df.iterrows():
                if row_index % 10 == 0:
                    progress = (row_index + 1) / total_rows * 100
                    progress_var.set(f"Processing language data: {progress:.2f}% complete")
                    parent.update_idletasks()

                if pd.isna(korean_text) or pd.isna(french_text):
                    continue

                if korean_text and french_text and '\t' not in korean_text and '\t' not in french_text:
                    if korean_text not in whole_dict:
                        whole_dict[korean_text] = set()
                    whole_dict[korean_text].add(french_text)

            progress_var.set("Processing complete. Saving dictionary.")
            parent.update_idletasks()
            return whole_dict

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during processing: {str(e)}")
            return {}

    def search_one_line(query, whole_dict, match_type="contains"):
        results = set()
        if match_type == "contains":
            results.update((k, v) for k, vs in whole_dict.items() for v in vs if query.lower() in k.lower())
        else:
            if query in whole_dict:
                results.update((query, v) for v in whole_dict[query])
        return results

    def normalize_text(text):
        text = re.sub(r'<color=.*?>|</color>', '', text)
        text = text.lower()
        text = text.replace("\\n", " ")
        text = text.replace("♨", "")
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = re.sub(r'(^[^\w\s\[\]]+|[^\w\s\[\]]+$)', '', text)
        return text

    def is_korean(text):
        return bool(re.search(r'[\uac00-\ud7a3]', text))

    version_var = tk.StringVar(value="PC")
    category_vars = []
    glossary_category_vars = []
    lookup_category_vars = []
    
    PC_CATEGORIES = [
        ('0', 'Item'), 
        ('18', 'Quest'), 
        ('6', 'Character'), 
        ('10', 'Skill'), 
        ('50', 'Cash Product'),
        ('37', 'StringTable')
    ]
    
    MOBILE_CATEGORIES = [
        ('0', 'Item'), 
        ('21', 'Quest'), 
        ('1', 'Character'), 
        ('28', 'Skill'), 
        ('6', 'Cash Product'), 
        ('20', 'Portal'), 
        ('30', 'Stage'), 
        ('15', 'Knowledge'), 
        ('41', 'Event'),
    ]


    def update_category_frames(*args):
        nonlocal glossary_category_vars, lookup_category_vars
        glossary_category_vars.clear()
        lookup_category_vars.clear()
        
        if version_var.get() == "CROSS":
            for widget in category_frame.winfo_children():
                widget.destroy()
            category_frame.pack_forget()
            
            # Clear all existing widgets in both frames
            for widget in glossary_category_frame.winfo_children():
                widget.destroy()
            for widget in lookup_category_frame.winfo_children():
                widget.destroy()
                
            # Create single platform selection frames
            glossary_platform_frame = tk.Frame(glossary_category_frame)
            glossary_platform_frame.pack(fill="x", pady=5)
            tk.Radiobutton(glossary_platform_frame, text="PC", variable=glossary_platform_var, 
                          value="PC").pack(side=tk.LEFT)
            tk.Radiobutton(glossary_platform_frame, text="MOBILE", variable=glossary_platform_var, 
                          value="MOBILE").pack(side=tk.LEFT)
            
            lookup_platform_frame = tk.Frame(lookup_category_frame)
            lookup_platform_frame.pack(fill="x", pady=5)
            tk.Radiobutton(lookup_platform_frame, text="PC", variable=lookup_platform_var, 
                          value="PC").pack(side=tk.LEFT)
            tk.Radiobutton(lookup_platform_frame, text="MOBILE", variable=lookup_platform_var, 
                          value="MOBILE").pack(side=tk.LEFT)
            
            glossary_category_frame.pack(pady=10, padx=10, fill="x")
            lookup_category_frame.pack(pady=10, padx=10, fill="x")
            
            update_glossary_categories()
            update_lookup_categories()
        else:
            # Unpack and clear CROSS platform specific frames
            glossary_category_frame.pack_forget()
            lookup_category_frame.pack_forget()
            update_single_category_frame()
            category_frame.pack(pady=10)

    def update_glossary_categories(*args):
        nonlocal glossary_category_vars
        glossary_category_vars.clear()
        
        for widget in glossary_category_frame.winfo_children():
            if isinstance(widget, tk.Frame) and len(widget.winfo_children()) > 0:
                if isinstance(widget.winfo_children()[0], tk.Radiobutton):
                    continue
            widget.destroy()
        
        categories = PC_CATEGORIES if glossary_platform_var.get() == "PC" else MOBILE_CATEGORIES
        
        category_frame = tk.Frame(glossary_category_frame)
        category_frame.pack(fill="x", pady=5)
        
        all_var = tk.BooleanVar(value=False)
        all_cb = ttk.Checkbutton(category_frame, text="All Categories", 
                                variable=all_var, 
                                command=lambda: toggle_all(all_var, glossary_category_vars))
        all_cb.pack(anchor='w')
        
        for cat_id, cat_name in categories:
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(category_frame, text=f"{cat_name} ({cat_id})", variable=var)
            cb.pack(anchor='w')
            glossary_category_vars.append((cat_id, var))

    def update_lookup_categories(*args):
        nonlocal lookup_category_vars
        lookup_category_vars.clear()
        
        for widget in lookup_category_frame.winfo_children():
            if isinstance(widget, tk.Frame) and len(widget.winfo_children()) > 0:
                if isinstance(widget.winfo_children()[0], tk.Radiobutton):
                    continue
            widget.destroy()
        
        categories = PC_CATEGORIES if lookup_platform_var.get() == "PC" else MOBILE_CATEGORIES
        
        category_frame = tk.Frame(lookup_category_frame)
        category_frame.pack(fill="x", pady=5)
        
        all_var = tk.BooleanVar(value=False)
        all_cb = ttk.Checkbutton(category_frame, text="All Categories", 
                                variable=all_var, 
                                command=lambda: toggle_all(all_var, lookup_category_vars))
        all_cb.pack(anchor='w')
        
        for cat_id, cat_name in categories:
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(category_frame, text=f"{cat_name} ({cat_id})", variable=var)
            cb.pack(anchor='w')
            lookup_category_vars.append((cat_id, var))

    def update_single_category_frame():
        for widget in category_frame.winfo_children():
            widget.destroy()
        
        categories = PC_CATEGORIES if version_var.get() == "PC" else MOBILE_CATEGORIES
        
        all_var = tk.BooleanVar(value=False)
        all_cb = ttk.Checkbutton(category_frame, text="All Categories", 
                                variable=all_var, 
                                command=lambda: toggle_all(all_var, category_vars))
        all_cb.pack(anchor='w')
        
        category_vars.clear()
        for cat_id, cat_name in categories:
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(category_frame, text=f"{cat_name} ({cat_id})", variable=var)
            cb.pack(anchor='w')
            category_vars.append((cat_id, var))

    def toggle_all(all_var, category_vars_list):
        state = all_var.get()
        for _, var in category_vars_list:
            var.set(state)

    def create_condition_for_platform(platform, selected_categories):
        conditions = []
        for cat_id in selected_categories:
            if platform == "PC":
                conditions.append(f"(data[0] == '{cat_id}') & (data[4] == '0')")
            else:
                if cat_id == '21':
                    conditions.append(f"(data[0] == '{cat_id}') & (data[4] == '1')")
                else:
                    conditions.append(f"(data[0] == '{cat_id}') & (data[4] == '0')")
        return ' | '.join(conditions)


    def create_new_term_list_thread():
        source_file = filedialog.askopenfilename(title="신규 글로서리 추출할 파일", filetypes=[("Text Files", "*.txt")])
        if not source_file:
            return
        qs_source_file = filedialog.askopenfilename(title="비교를 위한 렝귀지 데이터", filetypes=[("Text Files", "*.txt")])
        if not qs_source_file:
            return
        output_file = filedialog.asksaveasfilename(title="저장 파일", defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not output_file:
            return

        def process():
            try:
                progress_var.set("Starting new term list creation process...")
                parent.update_idletasks()

                data = pd.read_csv(source_file, delimiter="\t", header=None, usecols=range(9), dtype=str)
                
                if version_var.get() == "CROSS":
                    condition = create_condition_for_platform(
                        glossary_platform_var.get(),
                        [cat_id for cat_id, var in glossary_category_vars if var.get()]
                    )
                else:
                    condition = create_condition_for_platform(
                        version_var.get(),
                        [cat_id for cat_id, var in category_vars if var.get()]
                    )
                
                if condition is None or not condition:
                    messagebox.showwarning("Warning", "Please select at least one category.")
                    return

                filtered_data = data[eval(condition)]
                filtered_data = filtered_data.dropna(subset=[5, 6])
                matched_data = pd.DataFrame({'Korean': filtered_data[5], 'French': filtered_data[6]})

                most_frequent_translations = matched_data.groupby('Korean')['French'].apply(
                    lambda x: x.value_counts().index[0]).reset_index()
                
                unique_terms = dict(zip(most_frequent_translations['Korean'], 
                                    most_frequent_translations['French']))

                progress_var.set(f"Base list created with {len(unique_terms)} unique terms.")
                parent.update_idletasks()

                optimized_baselist = []
                total_terms = len(unique_terms)
                
                for index, (kr_term, fr_term) in enumerate(unique_terms.items()):
                    words = kr_term.split()
                    if len(words) >= 3:
                        search_words_count = (len(words) + 1) // 2
                        left_subset = " ".join(words[:search_words_count])
                        right_subset = " ".join(words[-search_words_count:])
                        shortest_subset = min(left_subset, right_subset, key=len)
                        optimized_baselist.append((kr_term, fr_term, len(shortest_subset)))
                    else:
                        optimized_baselist.append((kr_term, fr_term, len(kr_term)))
                    
                    if (index + 1) % 10 == 0:
                        progress = (index + 1) / total_terms * 100
                        progress_var.set(f"Optimized {index+1}/{total_terms} terms ({progress:.2f}%)")
                        parent.update_idletasks()

                optimized_baselist.sort(key=lambda x: x[2])
                final_baselist = []
                
                for index, (kr_term, fr_term, _) in enumerate(optimized_baselist):
                    is_subset = any(kr_term in other_kr and kr_term != other_kr 
                                  for other_kr, _ in final_baselist)
                    if not is_subset:
                        final_baselist.append((kr_term, fr_term))

                progress_var.set("Creating Quick Search dictionary...")
                parent.update_idletasks()
                whole_dict = process_data(qs_source_file, progress_var)

                progress_var.set("Starting new term identification...")
                parent.update_idletasks()
                new_terms = []
                total_terms = len(final_baselist)
                
                for i, (kr_term, fr_term) in enumerate(final_baselist):
                    results = search_one_line(kr_term, whole_dict, "contains")
                    if not results:
                        new_terms.append(f"{kr_term}\t{fr_term}")
                    
                    if (i + 1) % 10 == 0:
                        progress = (i + 1) / total_terms * 100
                        progress_var.set(f"Processed {i+1}/{total_terms} terms ({progress:.2f}%)")
                        parent.update_idletasks()

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_terms))

                progress_var.set(f"New term list created with {len(new_terms)} terms")
                parent.update_idletasks()
                messagebox.showinfo("Success", 
                                  f"New term list with {len(new_terms)} terms created and saved to {output_file}")

            except Exception as e:
                error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                print(error_message)
                progress_var.set(error_message)
                parent.update_idletasks()
                messagebox.showerror("Error", error_message)

        thread = threading.Thread(target=process)
        thread.start()



    def check_translation_consistency_thread():
        global active_dialog
        active_dialog = tk.Toplevel()
        dialog = active_dialog      
        dialog.title("Glossary Autocheck")
        dialog.geometry("600x600")
        dialog.transient(window)
        dialog.grab_set()
        
        center_dialog(dialog, window)
        
        files = {
            'language': tk.StringVar(),
            'close': tk.StringVar()
        }
        
        success_color = "#90EE90"
        default_color = "#f0f0f0"
        
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        upload_frame = tk.LabelFrame(main_frame, 
                                    text=UI_LANGUAGES[current_ui_language]['file_upload'], 
                                    padx=10, pady=10)
        upload_frame.pack(fill=tk.X, pady=10)
        
        buttons = {}
        glossary_radios = []
        lookup_radios = []
        
        def update_radios_state():
            has_language = bool(files['language'].get())
            has_close = bool(files['close'].get())
            
            for radio in glossary_radios:
                if radio['value'] == 'language':
                    radio.config(state=tk.NORMAL if has_language else tk.DISABLED)
                elif radio['value'] == 'close':
                    radio.config(state=tk.NORMAL if has_close else tk.DISABLED)
                elif radio['value'] == 'both':
                    radio.config(state=tk.NORMAL if (has_language and has_close) else tk.DISABLED)
                    
            for radio in lookup_radios:
                if radio['value'] == 'language':
                    radio.config(state=tk.NORMAL if has_language else tk.DISABLED)
                elif radio['value'] == 'close':
                    radio.config(state=tk.NORMAL if has_close else tk.DISABLED)
                elif radio['value'] == 'both':
                    radio.config(state=tk.NORMAL if (has_language and has_close) else tk.DISABLED)
        
        def update_process_button():
            if (glossary_type_var.get() and lookup_type_var.get() and 
                ((glossary_type_var.get() == "language" and files['language'].get()) or
                 (glossary_type_var.get() == "close" and files['close'].get()) or
                 (glossary_type_var.get() == "both" and files['language'].get() and files['close'].get())) and
                ((lookup_type_var.get() == "language" and files['language'].get()) or
                 (lookup_type_var.get() == "close" and files['close'].get()) or
                 (lookup_type_var.get() == "both" and files['language'].get() and files['close'].get()))):
                process_button.config(state=tk.NORMAL, bg=success_color)
            else:
                process_button.config(state=tk.DISABLED, bg=default_color)
        
        def select_file(file_type):
            filename = filedialog.askopenfilename(
                title=f"Select {file_type.title()} File",
                filetypes=[("Text Files", "*.txt")]
            )
            if filename:
                files[file_type].set(filename)
                buttons[file_type].config(
                    text=UI_LANGUAGES[current_ui_language][f'{file_type}_data_uploaded'],
                    bg=success_color
                )
                update_radios_state()
                update_process_button()
        
        for file_type in ['language', 'close']:
            buttons[file_type] = tk.Button(
                upload_frame,
                text=UI_LANGUAGES[current_ui_language][f'select_{file_type}_data'],
                command=lambda ft=file_type: select_file(ft),
                width=30,
                height=2,
                font=('Arial', 10, 'bold')
            )
            buttons[file_type].pack(pady=5)
        
        glossary_frame = tk.LabelFrame(main_frame, 
                                      text=UI_LANGUAGES[current_ui_language]['glossary_base_selection'], 
                                      padx=10, pady=10)
        glossary_frame.pack(fill=tk.X, pady=10)
        
        glossary_type_var = tk.StringVar(value="")
        for text_key, value in [("use_language_data", "language"), 
                               ("use_close_data", "close"), 
                               ("use_both_combined", "both")]:
            radio = tk.Radiobutton(
                glossary_frame, 
                text=UI_LANGUAGES[current_ui_language][text_key],
                variable=glossary_type_var,
                value=value,
                state=tk.DISABLED,
                command=update_process_button
            )
            radio.pack(anchor='w')
            glossary_radios.append(radio)
        
        lookup_frame = tk.LabelFrame(main_frame, 
                                    text=UI_LANGUAGES[current_ui_language]['glossary_crosscheck_selection'], 
                                    padx=10, pady=10)
        lookup_frame.pack(fill=tk.X, pady=10)
        
        lookup_type_var = tk.StringVar(value="")
        for text_key, value in [("check_language_data", "language"), 
                               ("check_close_data", "close"), 
                               ("check_both_combined", "both")]:
            radio = tk.Radiobutton(
                lookup_frame, 
                text=UI_LANGUAGES[current_ui_language][text_key],
                variable=lookup_type_var,
                value=value,
                state=tk.DISABLED,
                command=update_process_button
            )
            radio.pack(anchor='w')
            lookup_radios.append(radio)
        
        process_button = tk.Button(
            main_frame,
            text=UI_LANGUAGES[current_ui_language]['start_crosscheck'],
            state=tk.DISABLED,
            width=40,
            height=2,
            bg=default_color,
            font=('Arial', 12, 'bold')
        )
        process_button.pack(pady=20)
        
        def start_process():
            output_file = filedialog.asksaveasfilename(
                title="Save Results", 
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")]
            )
            if not output_file:
                return
                
            output_file_details = f"{os.path.splitext(output_file)[0]}_details.txt"
            dialog.destroy()

            def process():
                try:
                    progress_var.set("Starting translation consistency check process...")
                    parent.update_idletasks()

                    if version_var.get() == "CROSS":
                        glossary_categories = [cat_id for cat_id, var in glossary_category_vars if var.get()]
                        lookup_categories = [cat_id for cat_id, var in lookup_category_vars if var.get()]
                        
                        glossary_condition = create_condition_for_platform(
                            glossary_platform_var.get(), 
                            glossary_categories
                        )
                        lookup_condition = create_condition_for_platform(
                            lookup_platform_var.get(),
                            lookup_categories
                        )
                    else:
                        selected_categories = [cat_id for cat_id, var in category_vars if var.get()]
                        condition = create_condition_for_platform(version_var.get(), selected_categories)
                        glossary_condition = lookup_condition = condition

                    if glossary_condition is None or not glossary_condition:
                        messagebox.showwarning("Warning", "Please select at least one category.")
                        return

                    if glossary_type_var.get() == "language":
                        base_list_file = files['language'].get()
                    elif glossary_type_var.get() == "close":
                        base_list_file = files['close'].get()
                    else:  # both
                        base_list_file = "temp_combined_glossary.txt"
                        with open(base_list_file, 'w', encoding='utf-8') as outfile:
                            for f in [files['language'].get(), files['close'].get()]:
                                with open(f, 'r', encoding='utf-8') as infile:
                                    outfile.write(infile.read())

                    if lookup_type_var.get() == "language":
                        qs_source_file = files['language'].get()
                    elif lookup_type_var.get() == "close":
                        qs_source_file = files['close'].get()
                    else:  # both
                        qs_source_file = "temp_combined_lookup.txt"
                        with open(qs_source_file, 'w', encoding='utf-8') as outfile:
                            for f in [files['language'].get(), files['close'].get()]:
                                with open(f, 'r', encoding='utf-8') as infile:
                                    outfile.write(infile.read())

                    data = pd.read_csv(base_list_file, delimiter="\t", header=None, usecols=range(9), dtype=str)
                    filtered_data = data[eval(glossary_condition)]
                    filtered_data = filtered_data.dropna(subset=[5, 6])
                    matched_data = pd.DataFrame({
                        'Korean': filtered_data[5], 
                        'French': filtered_data[6], 
                        'category_number': filtered_data[0]
                    })
                    
                    matched_data = matched_data[matched_data['Korean'].str.len() > 1]

                    def select_translation(group):
                        translation_counts = group['French'].value_counts()
                        top_translations = translation_counts[translation_counts == translation_counts.max()]
                        
                        if len(top_translations) > 1:
                            item_translation = group[(group['category_number'] == '0') & 
                                                  (group['French'].isin(top_translations.index))]
                            if not item_translation.empty:
                                return item_translation['French'].iloc[0]
                        
                        return translation_counts.idxmax()

                    most_frequent_translations = matched_data.groupby('Korean').apply(select_translation).reset_index()
                    most_frequent_translations.columns = ['Korean', 'French']

                    base_list = [(kr, fr, normalize_text(kr), normalize_text(fr)) 
                                for kr, fr in zip(most_frequent_translations['Korean'],
                                                most_frequent_translations['French'])]

                    progress_var.set(f"Base list loaded. Total unique pairs: {len(base_list)}")
                    parent.update_idletasks()

                    progress_var.set("Creating Quick Search dictionaries...")
                    parent.update_idletasks()
                    whole_dict = process_data(qs_source_file, progress_var)
                    
                    progress_var.set("Starting initial consistency check...")
                    parent.update_idletasks()
                    potential_inconsistencies = []
                    total_pairs = len(base_list)

                    for i, (orig_kr, orig_fr, norm_kr, norm_fr) in enumerate(base_list, 1):
                        if i % 100 == 0:
                            progress_var.set(f"Initial consistency check: {i}/{total_pairs} pairs processed")
                            parent.update_idletasks()

                        primary_results = search_one_line(norm_kr, whole_dict, "contains")
                        primary_fr_tokens = {fr for _, fr in primary_results}

                        inconsistent_tokens = set()
                        for fr_token in primary_fr_tokens:
                            norm_fr_token = normalize_text(fr_token)
                            if norm_fr not in norm_fr_token and not is_korean(fr_token):
                                related_terms = [fr for _, _, kr, fr in base_list if norm_kr in kr and kr != norm_kr]
                                if not any(normalize_text(related_fr) in norm_fr_token for related_fr in related_terms):
                                    inconsistent_tokens.add(fr_token)

                        if 0 < len(inconsistent_tokens) <= 5:
                            potential_inconsistencies.append((orig_kr, orig_fr, inconsistent_tokens))

                    progress_var.set("Starting false positive filtering...")
                    parent.update_idletasks()
                    fr_token_occurrences = {}
                    
                    for i, (orig_kr, orig_fr, norm_kr, norm_fr) in enumerate(base_list, 1):
                        if i % 100 == 0:
                            progress = (i / len(base_list)) * 100
                            progress_var.set(f"PART 2 - False positive check: {progress:.2f}% complete")
                            parent.update_idletasks()

                        results = search_one_line(norm_kr, whole_dict, "contains")
                        for _, fr in results:
                            normalized_fr = normalize_text(fr)
                            if normalized_fr not in fr_token_occurrences:
                                fr_token_occurrences[normalized_fr] = set()
                            fr_token_occurrences[normalized_fr].add(orig_kr)

                    progress_var.set("Performing final filtering...")
                    parent.update_idletasks()
                    final_inconsistencies = []
                    MAX_TOKEN_LENGTH = 5000

                    for orig_kr, orig_fr, inconsistent_tokens in potential_inconsistencies:
                        truly_inconsistent_tokens = set()
                        norm_orig_fr = normalize_text(orig_fr)
                        
                        for token in inconsistent_tokens:
                            normalized_token = normalize_text(token)
                            if (normalized_token != norm_orig_fr and 
                                orig_kr in fr_token_occurrences.get(normalized_token, set()) and 
                                len(token) <= MAX_TOKEN_LENGTH):
                                truly_inconsistent_tokens.add(token)
                        
                        if truly_inconsistent_tokens:
                            final_inconsistencies.append((orig_kr, orig_fr, truly_inconsistent_tokens))

                    progress_var.set("Writing results to files...")
                    parent.update_idletasks()
                    
                    with open(output_file, 'w', encoding='utf-8') as f, \
                         open(output_file_details, 'w', encoding='utf-8') as f_details:
                        for orig_kr, orig_fr, inconsistent_tokens in final_inconsistencies:
                            f.write(f"{orig_kr}\n")
                            f_details.write(f"기준 KR: {orig_kr}\n")
                            f_details.write(f"기준 번역: {orig_fr}\n")
                            f_details.write("통일성 이슈:\n")
                            for token in inconsistent_tokens:
                                f_details.write(f"  {token}\n")
                            f_details.write("\n")

                    if glossary_type_var.get() == "both":
                        os.remove("temp_combined_glossary.txt")
                    if lookup_type_var.get() == "both":
                        os.remove("temp_combined_lookup.txt")

                    progress_var.set("Consistency check complete!")
                    parent.update_idletasks()
                    messagebox.showinfo("Success", 
                                      f"Consistency check complete!\n"
                                      f"Results saved to {output_file}\n"
                                      f"Details saved to {output_file_details}")

                except Exception as e:
                    error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                    print(error_message)
                    progress_var.set(error_message)
                    parent.update_idletasks()
                    messagebox.showerror("Error", error_message)

            thread = threading.Thread(target=process)
            thread.start()
        
        process_button.config(command=start_process)
        
        dialog.mainloop()


    glossary_category_frame = tk.LabelFrame(parent, text="Glossary Categories")
    lookup_category_frame = tk.LabelFrame(parent, text="Lookup Categories")
    
    glossary_platform_var = tk.StringVar(value="PC")
    lookup_platform_var = tk.StringVar(value="MOBILE")

    version_frame = tk.Frame(parent)
    version_frame.pack(pady=10)

    version_label = tk.Label(version_frame, 
                          text=UI_LANGUAGES[current_ui_language]['platform_select'], 
                          font='Helvetica 10 bold')
    version_label.pack(side=tk.LEFT)

    pc_radio = tk.Radiobutton(version_frame, text="PC", font='Helvetica 10 bold', 
                           variable=version_var, value="PC")
    mobile_radio = tk.Radiobutton(version_frame, text="MOBILE", font='Helvetica 10 bold', 
                               variable=version_var, value="MOBILE")
    cross_platform_radio = tk.Radiobutton(version_frame, text="CROSS", font='Helvetica 10 bold',
                                       variable=version_var, value="CROSS")
    pc_radio.pack(side=tk.LEFT)
    mobile_radio.pack(side=tk.LEFT)
    cross_platform_radio.pack(side=tk.LEFT)

    category_frame = tk.Frame(parent)
    update_single_category_frame()
    category_frame.pack(pady=10)
    
    version_var.trace('w', update_category_frames)
    glossary_platform_var.trace('w', update_glossary_categories)
    lookup_platform_var.trace('w', update_lookup_categories)

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=10)

    new_term_list_button = tk.Button(button_frame, 
                                  text=UI_LANGUAGES[current_ui_language]['new_terms_glossary'], 
                                  font='Helvetica 10 bold', 
                                  command=create_new_term_list_thread)
    new_term_list_button.pack(side=tk.LEFT, padx=15)

    consistency_check_button = tk.Button(button_frame, 
                                     text=UI_LANGUAGES[current_ui_language]['glossary_crosscheck'], 
                                     font='Helvetica 10 bold', 
                                     command=check_translation_consistency_thread)
    consistency_check_button.pack(side=tk.LEFT, padx=15)

    progress_var = tk.StringVar()
    progress_label = tk.Label(parent, textvariable=progress_var, wraplength=750)
    progress_label.pack(pady=10)



# Create main window
window = tk.Tk()
window.title("Quick Search - Version: 0305 (By Neil)")
window.geometry("800x800")
window.iconbitmap("images/QSico.ico")

window.bind_all("<MouseWheel>", on_mousewheel)
window.bind('<Control-c>', on_copy)

# Create notebook for tabs
notebook = ttk.Notebook(window)
notebook.pack(expand=True, fill='both')

# Create the frames for each tab
quick_search_tab = ttk.Frame(notebook)
glossary_checker_tab_frame = ttk.Frame(notebook)

# Add the tabs to the notebook
notebook.add(quick_search_tab, text='Quick Search')
notebook.add(glossary_checker_tab_frame, text='Glossary Checker')

# Button frame for Quick Search
button_frame = tk.Frame(quick_search_tab)
button_frame.pack(pady=10)

# Common button style
button_style = {
    'font': ('Helvetica', 11, 'bold'),
    'relief': 'raised',
    'bd': 3
}

create_button = tk.Button(button_frame, 
                         text=UI_LANGUAGES[current_ui_language]['create_dict'],
                         command=create_dictionary_dialog,
                         **button_style)
create_button.pack(side=tk.LEFT, padx=8, pady=4)

load_button = tk.Button(button_frame, 
                       text=UI_LANGUAGES[current_ui_language]['load_dict'],
                       command=load_dictionary_dialog,
                       **button_style)
load_button.pack(side=tk.LEFT, padx=8, pady=4)

reference_button = tk.Button(button_frame, 
                           text=UI_LANGUAGES[current_ui_language]['reference_off'],
                           command=toggle_reference,
                           state=tk.DISABLED,
                           bg="grey",
                           **button_style)
reference_button.pack(side=tk.LEFT, padx=8, pady=4)

settings_button = tk.Button(button_frame, 
                          text=UI_LANGUAGES[current_ui_language]['settings'],
                          command=open_settings,
                          **button_style)
settings_button.pack(side=tk.LEFT, padx=8, pady=4)

# Progress label
progress_var = tk.StringVar()
progress_label = tk.Label(quick_search_tab, textvariable=progress_var)
progress_label.pack()

# Progress Bar
progress_frame = tk.Frame(quick_search_tab)
progress_var = tk.StringVar()
progress_label = tk.Label(progress_frame, textvariable=progress_var)
progress_label.pack()
progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate')

def show_progress():
    search_frame.pack_forget()  # Hide search frame temporarily
    progress_frame.pack(pady=5, after=button_frame)  # Show progress frame below buttons
    progress_bar.pack(pady=5)
    search_frame.pack(pady=10, after=progress_frame)  # Show search frame below progress
    window.update_idletasks()

def hide_progress():
    progress_frame.pack_forget()
    progress_var.set("")
    progress_bar['value'] = 0
    window.update_idletasks()



# Search frame
search_frame = tk.Frame(quick_search_tab)
search_frame.pack(pady=10)


# Create a container frame that adjusts its size based on the active entry
search_entry_container = tk.Frame(search_frame)  
search_entry_container.pack(side=tk.TOP, fill=tk.X)

default_font = ('TkDefaultFont', 13)  # Use system default font for better compatibility

# Create the one-line entry with default font
one_line_search_entry = tk.Entry(search_entry_container, 
                                font=default_font,
                                width=80)
one_line_search_entry.pack(ipady=8)
one_line_search_entry.bind("<Return>", on_search_click)

# Create the multi-line entry with the same default font
multi_line_search_entry = tk.Text(search_entry_container, 
                                 height=10,
                                 width=80,
                                 font=default_font)
multi_line_search_entry.bind("<Return>", lambda event: on_search_click(event) or 'break')
multi_line_search_entry.bind("<Shift-Return>", lambda event: multi_line_search_entry.insert(tk.INSERT, ""))


def switch_search_type():
    if search_type_var.get() == "one_line":
        multi_line_search_entry.pack_forget()
        search_entry_container.configure(height=50)
        one_line_search_entry.pack(ipady=8)
        load_more_button.config(state=tk.NORMAL)
    else:
        one_line_search_entry.pack_forget()
        search_entry_container.configure(height=150)
        multi_line_search_entry.pack(fill=tk.BOTH, expand=True)
        load_more_button.config(state=tk.DISABLED)

# Search options
search_options_frame = tk.Frame(search_frame)
search_options_frame.pack(side=tk.TOP)

search_button = tk.Button(search_options_frame, 
                         text=UI_LANGUAGES[current_ui_language]['search'],
                         command=on_search_click,
                         width=10,  # Reduced from 15
                         height=1,  # Reduced from 2
                         font=('Helvetica', 11, 'bold'),  # Slightly smaller font
                         relief='raised',
                         bd=3)
search_button.pack(side=tk.LEFT, padx=8, pady=4)  # Slightly reduced padding

match_type_var = tk.StringVar(value="contains")
contains_radio = tk.Radiobutton(search_options_frame, text="Contains", 
                               variable=match_type_var, value="contains")
contains_radio.pack(side=tk.LEFT)

exact_radio = tk.Radiobutton(search_options_frame, text="Exact Match", 
                            variable=match_type_var, value="exact")
exact_radio.pack(side=tk.LEFT)


# Results frame
result_frame = tk.Frame(quick_search_tab)
result_frame.pack(pady=10, expand=True, fill=tk.BOTH)

canvas = tk.Canvas(result_frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scroll_bar = tk.Scrollbar(result_frame, orient="vertical", command=canvas.yview)
scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)

canvas.configure(yscrollcommand=scroll_bar.set)

# Create a frame inside the canvas to hold the results
result_container = tk.Frame(canvas)
canvas.create_window((0, 0), window=result_container, anchor='nw', tags='result_container')

def on_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

result_container.bind("<Configure>", on_frame_configure)

def on_canvas_configure(event):
    canvas.itemconfig('result_container', width=event.width)

canvas.bind('<Configure>', on_canvas_configure)

# Configure resizing behavior
quick_search_tab.columnconfigure(0, weight=1)
quick_search_tab.rowconfigure(0, weight=0)  # Button frame
quick_search_tab.rowconfigure(1, weight=0)  # Progress frame
quick_search_tab.rowconfigure(2, weight=0)  # Search frame
quick_search_tab.rowconfigure(3, weight=1)  # Result frame (needs to expand)

result_frame.columnconfigure(0, weight=1)
result_frame.rowconfigure(0, weight=1)



# Bottom frame
bottom_frame = tk.Frame(quick_search_tab)
bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

load_more_button = tk.Button(bottom_frame, text="Load More Results", command=load_more_results)
load_more_button.pack(side=tk.LEFT, padx=5)

search_type_var = tk.StringVar(value="one_line")
one_line_radio = tk.Radiobutton(bottom_frame, text="One Line", 
                               variable=search_type_var, value="one_line", 
                               command=switch_search_type)
one_line_radio.pack(side=tk.LEFT, padx=5)
multi_line_radio = tk.Radiobutton(bottom_frame, text="Multi Line", 
                                 variable=search_type_var, value="multi_line", 
                                 command=switch_search_type)
multi_line_radio.pack(side=tk.LEFT, padx=5)








def toggle_normalize():
    normalize_display_var.set(not normalize_display_var.get())
    normalize_button.config(text=f"Normalize: {'ON' if normalize_display_var.get() else 'OFF'}")
    if split_dict or whole_dict:
        display_results(50, append=False)

normalize_display_var = tk.BooleanVar(value=False)
normalize_button = tk.Button(bottom_frame, text="Normalize: OFF", 
                           command=lambda: toggle_normalize())
normalize_button.pack(side=tk.LEFT, padx=5)


def toggle_string_key():
    global show_string_key
    show_string_key = not show_string_key
    string_key_button.config(text=f"String Key: {'ON' if show_string_key else 'OFF'}")
    
    # Clear and reconfigure the grid
    for widget in result_container.winfo_children():
        widget.destroy()
    
    # Reset grid column configurations
    for i in range(result_container.grid_size()[0]):
        result_container.grid_columnconfigure(i, weight=0)
    
    # Redisplay results if dictionary is loaded
    if split_dict or whole_dict:
        display_results(50, append=False)
    
    # Update display after brief delay to ensure proper resizing
    window.after(100, lambda: result_container.update_idletasks())

string_key_button = tk.Button(bottom_frame, text="String Key: ON", command=toggle_string_key)
string_key_button.pack(side=tk.LEFT, padx=5)





# Initialize dictionaries and settings
split_dict = {}
whole_dict = {}
ref_split_dict = {}
ref_whole_dict = {}
search_results = []
current_index = 0
reference_active = False
show_string_key = True  # Add string key toggle state
string_keys = {}  # Dictionary to store string keys for both split and whole dict entries

# Load settings
load_settings()

# Set up the glossary checker tab
glossary_checker_tab(glossary_checker_tab_frame)


def on_closing():
    window.destroy()
    sys.exit()

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    center_x = int(screen_width / 2 - width / 2)
    center_y = int(screen_height / 2 - height / 2)
    window.geometry(f'{width}x{height}+{center_x}+{center_y}')

def center_dialog(dialog, parent):
    # Wait for the dialog to be rendered
    dialog.update_idletasks()
    
    # Get the parent window position and size
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    
    # Get dialog size
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    
    # Calculate position
    x = parent_x + (parent_width - dialog_width) // 2
    y = parent_y + (parent_height - dialog_height) // 2
    
    # Set the position
    dialog.geometry(f"+{x}+{y}")

def on_tab_changed(event):
    selected_tab = event.widget.select()
    tab_text = event.widget.tab(selected_tab, "text")
    
    # Store current position before resizing
    current_x = window.winfo_x()
    current_y = window.winfo_y()
    
    # Just adjust size based on selected tab
    if tab_text == 'Quick Search':
        new_width, new_height = 1100, 900
    elif tab_text == 'Glossary Checker':
        new_width, new_height = 600, 700
    else:
        return
    
    # Update geometry while maintaining position
    window.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")

notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
window.protocol("WM_DELETE_WINDOW", on_closing)

# Load settings at startup
load_settings()

if splash_active:
    pyi_splash.close()

# Start the main event loop
window.mainloop()