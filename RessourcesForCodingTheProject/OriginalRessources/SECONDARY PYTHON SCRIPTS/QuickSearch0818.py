print("- Quick Search XML - ver. 0818 (By Neil)")
print("- Quick Search XML - ver. 0818 (By Neil)")
print("- Quick Search XML - ver. 0818 (By Neil)")
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
import xml.etree.ElementTree as ET
from lxml import etree
from collections import defaultdict
import datetime
import ahocorasick

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
GAMES = ['BDO', 'BDM', 'BDC', 'CD']
LANGUAGES = ['DE', 'IT', 'PL', 'EN', 'ES', 'SP', 'FR', 'ID', 'JP', 'PT', 'RU', 'TR', 'TH', 'TW', 'CH']

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
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))
        
def tokenize(text):
    if isinstance(text, str) and text.strip() != '' and '\t' not in text:
        return re.split(r'\\?\n|\n', text)
    else:
        return []

def post_process_newlines(text):
    return str(text).replace("\n", "\n")
    
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
        with open(os.path.join(get_base_dir(), 'qs_settings.json'), 'w') as f:
            json.dump(font_settings, f)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

def load_settings():
    global font_settings, current_ui_language
    try:
        with open(os.path.join(get_base_dir(), 'qs_settings.json'), 'r') as f:
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
        display_results(50, append=False)

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
        display_results(50, append=False)
    
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
        display_results(50, append=False)

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
        display_results(50, append=False)
    
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
                dict_path = os.path.join(get_base_dir(), game, lang)
                if os.path.exists(dict_path):
                    if os.path.exists(os.path.join(dict_path, 'dictionary.pkl')):
                        self.dictionaries[game][lang] = {
                            'path': dict_path,
                            'active': False
                        }

    def create_dictionary(self, game, language, source_files):
        dict_path = os.path.join(get_base_dir(), game, language)
        os.makedirs(dict_path, exist_ok=True)

        split_dict, whole_dict, string_keys = process_data(source_files, progress_var)

        # Save if either dict has data
        if split_dict or whole_dict:
            dictionary_data = {
                'split_dict': split_dict,
                'whole_dict': whole_dict,
                'string_keys': string_keys,
                'creation_date': time.strftime("%m/%d %H:%M")
            }
            with open(os.path.join(dict_path, 'dictionary.pkl'), 'wb') as f:
                pickle.dump(dictionary_data, f)

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
            
            dict_path = os.path.join(get_base_dir(), game, language)
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

def create_dictionary_dialog():
    dialog = tk.Toplevel(window)
    dialog.title("Create New Dictionary")
    dialog.geometry("350x650")
    dialog.transient(window)
    dialog.grab_set()
    center_dialog(dialog, window)
    
    # Game selection
    game_frame = ttk.LabelFrame(dialog, text="Select Game")
    game_frame.pack(padx=10, pady=5, fill="x")
    
    game_var = tk.StringVar()
    lang_var = tk.StringVar()

    for game in GAMES:
        ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")
    
    # Language selection
    lang_frame = ttk.LabelFrame(dialog, text="Select Language")
    lang_frame.pack(padx=10, pady=5, fill="x")
    
    for lang in LANGUAGES:
        ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")
    
    # Selection mode
    mode_frame = ttk.LabelFrame(dialog, text="Source Selection Mode")
    mode_frame.pack(padx=10, pady=5, fill="x")
    mode_var = tk.StringVar(value="files")
    ttk.Radiobutton(mode_frame, text="Select Files (XML/TXT)", variable=mode_var, value="files").pack(anchor="w")
    ttk.Radiobutton(mode_frame, text="Select Folder (recursive)", variable=mode_var, value="folder").pack(anchor="w")
    
    def on_create():
        game = game_var.get()
        language = lang_var.get()
    
        if not game or not language:
            messagebox.showwarning("Warning", "Please select both game and language")
            return
        
        # Choose source based on mode
        if mode_var.get() == "files":
            source_files = filedialog.askopenfilenames(
                title="Select XML or TXT Files",
                filetypes=[
                    ("XML and TXT Files", "*.xml *.txt *.tsv"),
                    ("XML Files", "*.xml"),
                    ("Text Files", "*.txt;*.tsv"),
                    ("All Files", "*.*")
                ]
            )
            if not source_files:
                return
        else:
            folder_path = filedialog.askdirectory(title="Select Folder Containing XML/TXT Files")
            if not folder_path:
                return
            # Recursively collect XML and TXT/TSV files
            source_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith((".xml", ".txt", ".tsv")):
                        source_files.append(os.path.join(root, file))
            if not source_files:
                messagebox.showwarning("Warning", "No XML/TXT files found in selected folder.")
                return
    
        dialog.destroy()  # Close dialog before starting process
        progress_var.set(f"Creating {game} {language} dictionary...")
    
        def process():
            try:
                progress_var.set("Starting dictionary creation...")
                window.update_idletasks()
    
                split_d, whole_d, string_keys = process_data(source_files, progress_var)
                if split_d or whole_d:
                    dict_path = os.path.join(get_base_dir(), game, language)
                    os.makedirs(dict_path, exist_ok=True)
                    dictionary_data = {
                        'split_dict': split_d,
                        'whole_dict': whole_d,
                        'string_keys': string_keys,
                        'creation_date': time.strftime("%m/%d %H:%M")
                    }
                    with open(os.path.join(dict_path, 'dictionary.pkl'), 'wb') as f:
                        pickle.dump(dictionary_data, f)
                    dict_manager.load_available_dictionaries()
                    progress_var.set(f"{game} {language} dictionary created successfully.")
                    update_dictionary_buttons()
                else:
                    progress_var.set("Dictionary creation failed.")
    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create dictionary: {e}")
                traceback.print_exc()
            finally:
                window.after(2000, lambda: progress_var.set(""))
    
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

def process_data(source_files, progress_var):
    """
    Process selected files (XML or TXT tab-delimited) and build dictionaries.
    Returns (split_dict, whole_dict, string_keys).
    """
    split_dict = {}
    whole_dict = {}
    string_keys_split = []
    string_keys_whole = []
    global stringid_to_entry
    stringid_to_entry.clear()

    try:
        show_progress()
        progress_var.set("Detecting file type...")
        progress_bar['value'] = 5
        window.update_idletasks()

        if not source_files:
            messagebox.showwarning("Warning", "No files selected.")
            hide_progress()
            return {}, {}, {}

        first_ext = os.path.splitext(source_files[0])[1].lower()
        is_xml = first_ext == ".xml"
        is_txt = first_ext in (".txt", ".tsv")

        if not (is_xml or is_txt):
            messagebox.showerror("Error", f"Unsupported file type: {first_ext}")
            hide_progress()
            return {}, {}, {}

        total_files = len(source_files)

        if is_xml:
            # XML processing unchanged
            korean_lines_split, french_lines_split = [], []
            korean_lines_whole, french_lines_whole = [], []

            for idx, xml_path in enumerate(source_files, start=1):
                pct = 5 + (idx / total_files) * 30
                progress_var.set(f"Parsing XML [{idx}/{total_files}]: {os.path.basename(xml_path)}")
                progress_bar['value'] = pct
                window.update_idletasks()

                try:
                    tree = ET.parse(xml_path)
                    root_el = tree.getroot()
                except Exception:
                    continue

                for loc in root_el.findall('LocStr'):
                    ko = normalize_dictionary_text(loc.get('StrOrigin', '') or '')
                    fr = normalize_dictionary_text(loc.get('Str', '') or '')
                    sid = loc.get('StringId', '') or ''

                    if not ko or not fr:
                        continue

                    ko_toks = tokenize(ko)
                    fr_toks = tokenize(fr)

                    if ko_toks and len(ko_toks) == len(fr_toks):
                        for k_tok, f_tok in zip(ko_toks, fr_toks):
                            korean_lines_split.append(k_tok)
                            french_lines_split.append(f_tok)
                            string_keys_split.append((k_tok, sid))
                            if sid:
                                stringid_to_entry[sid] = (k_tok, f_tok)
                    else:
                        korean_lines_whole.append(ko)
                        french_lines_whole.append(fr)
                        string_keys_whole.append((ko, sid))
                        if sid:
                            stringid_to_entry[sid] = (ko, fr)

            for k, f, key_data in zip(korean_lines_split, french_lines_split, string_keys_split):
                split_dict.setdefault(k, []).append((f, key_data[1]))
            for k, f, key_data in zip(korean_lines_whole, french_lines_whole, string_keys_whole):
                whole_dict.setdefault(k, []).append((f, key_data[1]))

        elif is_txt:
            korean_lines_split, french_lines_split = [], []
            korean_lines_whole, french_lines_whole = [], []

            for idx, txt_path in enumerate(source_files, start=1):
                pct = 5 + (idx / total_files) * 5
                progress_var.set(f"Opening TXT [{idx}/{total_files}]: {os.path.basename(txt_path)}")
                progress_bar['value'] = pct
                window.update_idletasks()

                try:
                    df = pd.read_csv(
                        txt_path,
                        delimiter="\t",
                        header=None,
                        usecols=range(7),
                        dtype=str,
                        quoting=csv.QUOTE_NONE,
                        quotechar=None,
                        escapechar=None
                    )
                except Exception as e:
                    print(f"Error reading {txt_path}: {e}")
                    continue

                total_rows = len(df)
                for row_idx, row in df.iterrows():
                    # Update progress every 500 rows
                    if row_idx % 500 == 0 or row_idx == total_rows - 1:
                        file_progress = (row_idx + 1) / total_rows
                        overall_progress = ((idx - 1) + file_progress) / total_files
                        progress_bar['value'] = 10 + overall_progress * 80
                        progress_var.set(
                            f"Processing TXT [{idx}/{total_files}] "
                            f"Row {row_idx+1}/{total_rows} "
                            f"({overall_progress*100:.1f}%)"
                        )
                        window.update_idletasks()

                    korean_text = normalize_dictionary_text(row[5] or "")
                    french_text = normalize_dictionary_text(row[6] or "")
                    # Build StringID with NORMAL SPACES instead of tabs
                    str_key = " ".join(str(x).strip() if x is not None else '' for x in row[0:5])

                    if not korean_text or not french_text:
                        continue

                    korean_tokens = tokenize(korean_text)
                    french_tokens = tokenize(french_text)

                    if len(korean_tokens) == len(french_tokens) and korean_tokens:
                        for kr, fr in zip(korean_tokens, french_tokens):
                            korean_lines_split.append(kr)
                            french_lines_split.append(fr)
                            string_keys_split.append((kr, str_key))
                            stringid_to_entry[str_key] = (kr, fr)
                    else:
                        korean_lines_whole.append(korean_text)
                        french_lines_whole.append(french_text)
                        string_keys_whole.append((korean_text, str_key))
                        stringid_to_entry[str_key] = (korean_text, french_text)

            for k, f, key_data in zip(korean_lines_split, french_lines_split, string_keys_split):
                split_dict.setdefault(k, []).append((f, key_data[1]))
            for k, f, key_data in zip(korean_lines_whole, french_lines_whole, string_keys_whole):
                whole_dict.setdefault(k, []).append((f, key_data[1]))

        string_keys = {'split': string_keys_split, 'whole': string_keys_whole}

        progress_var.set("Dictionary creation complete!")
        progress_bar['value'] = 100
        window.update_idletasks()
        window.after(1000, hide_progress)
        return split_dict, whole_dict, string_keys

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during processing:\n{e}")
        hide_progress()
        return {}, {}, {}

def search_one_line(query, match_type="contains", start_index=0, limit=50):
    if not query or query.isspace():
        return []

    # --- StringId direct lookup (fast path) ---
    global stringid_to_entry
    results = []
    query_str = str(query).strip()
    if query_str in stringid_to_entry:
        kr, fr = stringid_to_entry[query_str]
        if reference_active and dict_manager.reference_dict:
            ref_fr = None
            if kr in ref_split_dict and ref_split_dict[kr]:
                ref_fr = ref_split_dict[kr][0][0]
            elif kr in ref_whole_dict and ref_whole_dict[kr]:
                ref_fr = ref_whole_dict[kr][0][0]
            return [(kr, fr, ref_fr, query_str)]  # Pass StringID directly
        else:
            return [(kr, fr, query_str)]  # Pass StringID directly

    try:
        query_lower = query.lower()

        def check_match(text1, text2, stringid):
            if match_type == "contains":
                return (
                    query_lower in str(text1).lower() or
                    query_lower in str(text2).lower() or
                    query_lower in str(stringid).lower()
                )
            return (
                query_lower == str(text1).lower() or
                query_lower == str(text2).lower() or
                query_lower == str(stringid).lower()
            )

        def is_valid_entry(kr, fr, stringid):
            # Changed to accept stringid as a direct string parameter
            if not kr.strip() or not fr.strip():
                return False
            return True

        # Search in main dictionary (KR-FR)
        for kr, translations in split_dict.items():
            for fr, stringid in translations:  # stringid is already a string here
                if check_match(str(kr), str(fr), stringid) and is_valid_entry(kr, fr, stringid):
                    if reference_active and dict_manager.reference_dict:
                        ref_fr = None
                        if kr in ref_split_dict and ref_split_dict[kr]:
                            ref_fr = ref_split_dict[kr][0][0]
                        elif kr in ref_whole_dict and ref_whole_dict[kr]:
                            ref_fr = ref_whole_dict[kr][0][0]
                        results.append((kr, fr, ref_fr, stringid))  # Pass StringID directly
                    else:
                        results.append((kr, fr, stringid))  # Pass StringID directly

        for kr, translations in whole_dict.items():
            for fr, stringid in translations:  # stringid is already a string here
                if check_match(str(kr), str(fr), stringid) and is_valid_entry(kr, fr, stringid):
                    if reference_active and dict_manager.reference_dict:
                        ref_fr = None
                        if kr in ref_split_dict and ref_split_dict[kr]:
                            ref_fr = ref_split_dict[kr][0][0]
                        elif kr in ref_whole_dict and ref_whole_dict[kr]:
                            ref_fr = ref_whole_dict[kr][0][0]
                        results.append((kr, fr, ref_fr, stringid))  # Pass StringID directly
                    else:
                        results.append((kr, fr, stringid))  # Pass StringID directly

        # Search in reference dictionary if active (EN)
        if reference_active and dict_manager.reference_dict:
            for kr, ref_translations in ref_split_dict.items():
                for ref_fr, _ in ref_translations:
                    if query_lower in str(ref_fr).lower():
                        fr = None
                        stringid = None
                        if kr in split_dict and split_dict[kr]:
                            fr, stringid = split_dict[kr][0]
                            if is_valid_entry(kr, fr, stringid):
                                results.append((kr, fr, ref_fr, stringid))
                        elif kr in whole_dict and whole_dict[kr]:
                            fr, stringid = whole_dict[kr][0]
                            if is_valid_entry(kr, fr, stringid):
                                results.append((kr, fr, ref_fr, stringid))

            for kr, ref_translations in ref_whole_dict.items():
                for ref_fr, _ in ref_translations:
                    if query_lower in str(ref_fr).lower():
                        fr = None
                        stringid = None
                        if kr in split_dict and split_dict[kr]:
                            fr, stringid = split_dict[kr][0]
                            if is_valid_entry(kr, fr, stringid):
                                results.append((kr, fr, ref_fr, stringid))
                        elif kr in whole_dict and whole_dict[kr]:
                            fr, stringid = whole_dict[kr][0]
                            if is_valid_entry(kr, fr, stringid):
                                results.append((kr, fr, ref_fr, stringid))

        results.sort(key=lambda x: len(str(x[0])))
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

    def is_valid_entry(kr, fr, stringid):
        # Changed to accept stringid as a direct string parameter
        if not kr.strip() or not fr.strip():
            return False
        return True

    for q in queries:
        # Try search by StringId first if q is all digits or looks like a StringId
        results = search_one_line(q, match_type, 0, 1)
        if results:
            if reference_active:
                kr, fr, ref_fr, stringid = results[0]  # stringid is already a string
                if is_valid_entry(kr, fr, stringid):
                    french_results.append(fr)
                    korean_results.append(kr)
                    ref_french_results.append(ref_fr if ref_fr else "❓❓")
                else:
                    french_results.append("❓❓")
                    korean_results.append("❓❓")
                    ref_french_results.append("❓❓")
            else:
                kr, fr, stringid = results[0]  # stringid is already a string
                if is_valid_entry(kr, fr, stringid):
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

# Update the display_results function - FIX FOR STRINGID DISPLAY ISSUE
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
                    korean, french, ref_french, stringid = result  # stringid is already a string
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        # Use stringid directly - it's already a string
                        key_cell = create_cell(result_container, stringid if stringid else "", 'korean', wraplength, display_idx, 0)
                        key_cell.grid(row=display_idx, column=0, sticky='nsew', padx=1, pady=1)

                    kr_cell = create_cell(result_container, korean, 'korean', wraplength, display_idx, col_offset)
                    fr_cell = create_cell(result_container, french, 'translation', wraplength, display_idx, col_offset + 1)
                    ref_cell = create_cell(result_container, ref_french if ref_french else "❓❓", 'reference', 
                                         wraplength, display_idx, col_offset + 2)

                    kr_cell.grid(row=display_idx, column=col_offset, sticky='nsew', padx=1, pady=1)
                    fr_cell.grid(row=display_idx, column=col_offset + 1, sticky='nsew', padx=1, pady=1)
                    ref_cell.grid(row=display_idx, column=col_offset + 2, sticky='nsew', padx=1, pady=1)
                else:
                    korean, french, stringid = result  # stringid is already a string
                    col_offset = 1 if show_string_key else 0
                    
                    if show_string_key:
                        # Use stringid directly - it's already a string
                        key_cell = create_cell(result_container, stringid if stringid else "", 'korean', wraplength, display_idx, 0)
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
                        if key_results:
                            stringid = key_results[0][3] if reference_active else key_results[0][2]
                            # stringid is already a string, use it directly
                        else:
                            stringid = ""
                        key_cell = create_cell(result_container, stringid, 'korean', wraplength, display_idx, 0)
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
                        if key_results:
                            stringid = key_results[0][2]
                            # stringid is already a string, use it directly
                        else:
                            stringid = ""
                        key_cell = create_cell(result_container, stringid, 'korean', wraplength, display_idx, 0)
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

def extract_locstr_from_xml(xml_path):
    pairs = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for locstr in root.findall('.//LocStr'):
            kr = locstr.get('StrOrigin', '').strip()
            tr = locstr.get('Str', '').strip()
            pairs.append((kr, tr))
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
    return pairs

def extract_all_pairs_from_files(file_list, progress_var=None, parent=None):
    """
    Adaptive extractor for both XML and TXT/TSV files.
    Returns a list of (StrOrigin, Str) pairs.
    """
    all_pairs = []
    total = len(file_list)

    for idx, file_path in enumerate(file_list, start=1):
        if progress_var and parent:
            progress_var.set(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
            parent.update_idletasks()

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".xml":
                # --- XML parsing ---
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    kr = locstr.get('StrOrigin', '').strip()
                    tr = locstr.get('Str', '').strip()
                    if kr or tr:
                        all_pairs.append((kr, tr))

            elif ext in (".txt", ".tsv"):
                # --- TXT/TSV parsing ---
                try:
                    # First, try to detect the actual number of columns
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        num_cols = len(first_line.split('\t'))
                    
                    # Ensure we read at least 7 columns if available
                    cols_to_read = max(7, num_cols) if num_cols > 0 else 7
                    
                    df = pd.read_csv(
                        file_path,
                        delimiter="\t",
                        header=None,
                        dtype=str,
                        quoting=csv.QUOTE_NONE,
                        quotechar=None,
                        escapechar=None,
                        na_values=[''],
                        keep_default_na=False
                    )
                    
                    # Check if we have the expected columns
                    if len(df.columns) >= 7:
                        for _, row in df.iterrows():
                            kr = str(row[5]).strip() if pd.notna(row[5]) else ""
                            tr = str(row[6]).strip() if pd.notna(row[6]) else ""
                            if kr or tr:
                                all_pairs.append((kr, tr))
                    else:
                        print(f"Warning: {file_path} has only {len(df.columns)} columns, expected at least 7")
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

            else:
                print(f"Skipping unsupported file type: {file_path}")

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    return all_pairs

def extract_all_pairs_from_folder(folder_path, progress_var=None, parent=None):
    """
    Recursively walk through folder and extract all (StrOrigin, Str) pairs
    from XML and TXT/TSV files.
    """
    all_pairs = []
    file_list = []

    # Collect XML, TXT, TSV files
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".xml", ".txt", ".tsv")):
                file_list.append(os.path.join(root, file))

    total = len(file_list)
    for idx, file_path in enumerate(file_list, start=1):
        if progress_var and parent:
            progress_var.set(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
            parent.update_idletasks()

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    kr = locstr.get('StrOrigin', '').strip()
                    tr = locstr.get('Str', '').strip()
                    if kr or tr:
                        all_pairs.append((kr, tr))

            elif ext in (".txt", ".tsv"):
                try:
                    # First, try to detect the actual number of columns
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        num_cols = len(first_line.split('\t'))
                    
                    # Ensure we read at least 7 columns if available
                    cols_to_read = max(7, num_cols) if num_cols > 0 else 7
                    
                    df = pd.read_csv(
                        file_path,
                        delimiter="\t",
                        header=None,
                        dtype=str,
                        quoting=csv.QUOTE_NONE,
                        quotechar=None,
                        escapechar=None,
                        na_values=[''],
                        keep_default_na=False
                    )
                    
                    # Check if we have the expected columns
                    if len(df.columns) >= 7:
                        for _, row in df.iterrows():
                            kr = str(row[5]).strip() if pd.notna(row[5]) else ""
                            tr = str(row[6]).strip() if pd.notna(row[6]) else ""
                            if kr or tr:
                                all_pairs.append((kr, tr))
                    else:
                        print(f"Warning: {file_path} has only {len(df.columns)} columns, expected at least 7")
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    return all_pairs

def is_korean(text):
    """
    Returns True if text contains any Korean syllable (U+AC00–U+D7A3).
    """
    return bool(re.search(r'[\uac00-\ud7a3]', text))

def glossary_checker_tab(parent):
    """
    Glossary Checker Tab with:
    - NEW: Changed to file selection instead of folder recursion
    - Sentence filtering option (entries ending with . ? !)
    - Glossary length threshold (user-defined)
    - Applies to Extract Glossary, Line Check, and Term Check
    - Term Check: robust filtering to avoid false positives for common words
    - NEW: For Line Check and Term Check, user can choose to build glossary from a custom folder
    - NEW: Pattern Sequence Check and Character Count Check for XML LocStr entries
    """

    # --- UI Variables ---
    progress_var = tk.StringVar(value="Ready")
    filter_sentences_var = tk.BooleanVar(value=True)
    glossary_length_var = tk.IntVar(value=15)  # Default threshold
    min_occurrence_var = tk.IntVar(value=2)
    sort_method_var = tk.StringVar(value="alphabetical")

    # --- Helper Functions ---

    def is_korean(text):
        return bool(re.search(r'[\uac00-\ud7a3]', text))

    def is_sentence(text):
        """Returns True if text ends with a sentence-ending punctuation."""
        return bool(re.search(r'[.?!]\s*$', text.strip()))

    def extract_all_pairs_from_files(file_list, progress_var=None, parent=None):
        """
        Adaptive extractor for both XML and TXT/TSV files.
        Returns a list of (StrOrigin, Str) pairs.
        """
        all_pairs = []
        total = len(file_list)

        for idx, file_path in enumerate(file_list, start=1):
            if progress_var and parent:
                progress_var.set(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
                parent.update_idletasks()

            ext = os.path.splitext(file_path)[1].lower()

            try:
                if ext == ".xml":
                    # --- XML parsing ---
                    parser = etree.XMLParser(recover=True, resolve_entities=False)
                    tree = etree.parse(file_path, parser)
                    for locstr in tree.xpath('//LocStr'):
                        kr = locstr.get('StrOrigin', '').strip()
                        tr = locstr.get('Str', '').strip()
                        if kr or tr:
                            all_pairs.append((kr, tr))

                elif ext in (".txt", ".tsv"):
                    # --- TXT/TSV parsing ---
                    try:
                        # First, try to detect the actual number of columns
                        with open(file_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline()
                            num_cols = len(first_line.split('\t'))
                        
                        # Ensure we read at least 7 columns if available
                        cols_to_read = max(7, num_cols) if num_cols > 0 else 7
                        
                        df = pd.read_csv(
                            file_path,
                            delimiter="\t",
                            header=None,
                            dtype=str,
                            quoting=csv.QUOTE_NONE,
                            quotechar=None,
                            escapechar=None,
                            na_values=[''],
                            keep_default_na=False
                        )
                        
                        # Check if we have the expected columns
                        if len(df.columns) >= 7:
                            for _, row in df.iterrows():
                                kr = str(row[5]).strip() if pd.notna(row[5]) else ""
                                tr = str(row[6]).strip() if pd.notna(row[6]) else ""
                                if kr or tr:
                                    all_pairs.append((kr, tr))
                        else:
                            print(f"Warning: {file_path} has only {len(df.columns)} columns, expected at least 7")
                            
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        continue

                else:
                    print(f"Skipping unsupported file type: {file_path}")

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

        return all_pairs

    def extract_all_locstrs_from_files(file_list, progress_var=None, parent=None):
        """
        Returns a list of dicts:
        [
            {
                'StrOrigin': ...,
                'Str': ...,
                'xml_path': ...,
                'locstr_id': ... (optional)
            },
            ...
        ]
        Supports XML and TXT/TSV.
        """
        all_entries = []
        total = len(file_list)

        for idx, file_path in enumerate(file_list, start=1):
            if progress_var and parent:
                progress_var.set(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
                parent.update_idletasks()

            ext = os.path.splitext(file_path)[1].lower()
            try:
                if ext == ".xml":
                    parser = etree.XMLParser(recover=True, resolve_entities=False)
                    tree = etree.parse(file_path, parser)
                    for locstr in tree.xpath('//LocStr'):
                        entry = {
                            'StrOrigin': locstr.get('StrOrigin', '').strip(),
                            'Str': locstr.get('Str', '').strip(),
                            'xml_path': file_path,
                            'locstr_id': locstr.get('ID', '')
                        }
                        all_entries.append(entry)

                elif ext in (".txt", ".tsv"):
                    try:
                        # First, try to detect the actual number of columns
                        with open(file_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline()
                            num_cols = len(first_line.split('\t'))
                        
                        # Ensure we read at least 7 columns if available
                        cols_to_read = max(7, num_cols) if num_cols > 0 else 7
                        
                        df = pd.read_csv(
                            file_path,
                            delimiter="\t",
                            header=None,
                            dtype=str,
                            quoting=csv.QUOTE_NONE,
                            quotechar=None,
                            escapechar=None,
                            na_values=[''],
                            keep_default_na=False
                        )
                        
                        # Check if we have the expected columns
                        if len(df.columns) >= 7:
                            for _, row in df.iterrows():
                                # Build StringID from first 5 columns like in process_data
                                str_key = " ".join(str(row[i]).strip() if pd.notna(row[i]) else '' for i in range(min(5, len(row))))
                                
                                entry = {
                                    'StrOrigin': str(row[5]).strip() if pd.notna(row[5]) else "",
                                    'Str': str(row[6]).strip() if pd.notna(row[6]) else "",
                                    'xml_path': file_path,
                                    'locstr_id': str_key
                                }
                                all_entries.append(entry)
                        else:
                            print(f"Warning: {file_path} has only {len(df.columns)} columns, expected at least 7")
                            
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        continue

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

        return all_entries

    def glossary_filter(pairs, length_threshold, filter_sentences, min_occurrence=None):
        """
        Filter for glossary extraction:
        - Source length < threshold
        - Both non-empty
        - Translation has no Korean
        - Optionally, source is not a sentence
        - NEW: Filter out if source contains ANY punctuation (including "..." and special ellipsis …)
        - Optionally, keep only entries that occur >= min_occurrence times
        Returns: filtered list of (kr, tr) tuples
        """
        import string
        filtered = []
        count_map = {}

        # First pass: basic filtering
        for kr, tr in pairs:
            if not kr or not tr:
                continue
            if len(kr) >= length_threshold:
                continue
            if is_korean(tr):
                continue
            if filter_sentences and re.search(r'[.?!]\s*$', kr.strip()):
                continue
            # NEW: Skip if any punctuation exists in source
            # Include special ellipsis character "…"
            if any(ch in string.punctuation for ch in kr) or '…' in kr:
                continue
            filtered.append((kr, tr))
            count_map[kr] = count_map.get(kr, 0) + 1

        # Second pass: apply min_occurrence if provided
        if min_occurrence is not None:
            filtered = [(kr, tr) for kr, tr in filtered if count_map.get(kr, 0) >= min_occurrence]

        return filtered

    # --- GLOSSARY EXTRACT (UPDATED WITH AHO-CORASICK) ---
    def extract_glossary_thread():
        xml_files = filedialog.askopenfilenames(
            title="Select Source XML/TXT Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("XML Files", "*.xml"),
                ("Text Files", "*.txt;*.tsv"),
                ("All Files", "*.*")
            ]
        )
        if not xml_files:
            return

        out = filedialog.asksaveasfilename(
            title="Save Glossary As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not out:
            return

        def task():
            try:
                start_time = time.time()
                
                print("\n" + "="*60)
                print("🚀 STARTING ULTRA-FAST GLOSSARY EXTRACTION WITH AHO-CORASICK")
                print("="*60)
                
                progress_var.set("Extracting initial glossary terms...")
                parent.update_idletasks()

                # STEP 1: Extract all candidate terms
                all_pairs = extract_all_pairs_from_files(xml_files, progress_var, parent)

                # 🔹 NEW FILTER: Ignore if Str contains Korean
                all_pairs = [(kr, tr) for kr, tr in all_pairs if not is_korean(tr)]

                filtered = glossary_filter(
                    all_pairs,
                    glossary_length_var.get(),
                    filter_sentences_var.get()
                )

                # Dedupe by first-seen StrOrigin
                seen = set()
                candidate_terms = []
                for kr, tr in filtered:
                    if kr not in seen:
                        candidate_terms.append((kr, tr))
                        seen.add(kr)

                if not candidate_terms:
                    progress_var.set("No candidate terms found.")
                    messagebox.showwarning("No terms", "No terms found with current filters.")
                    return

                print(f"📋 Found {len(candidate_terms):,} candidate terms")

                # STEP 2: Build Aho-Corasick automaton
                step2_start = time.time()
                progress_var.set("Building Aho-Corasick automaton...")
                parent.update_idletasks()
                print("\n🔧 STEP 2: Building Aho-Corasick automaton...")
                
                automaton = ahocorasick.Automaton()
                term_to_info = {}  # Map term to (kr, tr) tuple
                
                for kr, tr in candidate_terms:
                    automaton.add_word(kr, kr)
                    term_to_info[kr] = (kr, tr)
                
                automaton.make_automaton()
                step2_time = time.time() - step2_start
                print(f"   ✅ Automaton built in {step2_time:.2f}s")

                # STEP 3: ULTRA-FAST occurrence counting with Aho-Corasick
                step3_start = time.time()
                progress_var.set("Starting ULTRA-FAST Aho-Corasick occurrence counting...")
                parent.update_idletasks()
                print("\n⚡ STEP 3: LIGHTNING-FAST occurrence counting with Aho-Corasick...")
                
                term_text_sets = {kr: set() for kr, _ in candidate_terms}
                total_texts_scanned = 0
                
                for file_idx, xml_path in enumerate(xml_files, 1):
                    if file_idx % 10 == 0:
                        progress = (file_idx / len(xml_files)) * 100
                        texts_per_sec = total_texts_scanned / (time.time() - step3_start) if total_texts_scanned > 0 else 0
                        progress_var.set(f"Aho-Corasick scan: {progress:.1f}% ({texts_per_sec:.0f} texts/sec)")
                        parent.update_idletasks()
                        
                        if file_idx % 100 == 0:
                            print(f"      Progress: {file_idx:,}/{len(xml_files):,} files ({progress:.1f}%)")
                    
                    try:
                        tree = etree.parse(xml_path)
                        
                        for locstr_idx, locstr in enumerate(tree.xpath('//LocStr')):
                            src = locstr.get('StrOrigin', '').strip()
                            tgt = locstr.get('Str', '').strip()

                            # 🔹 NEW FILTER: Ignore if Str contains Korean
                            if is_korean(tgt):
                                continue

                            if not src:
                                continue
                            
                            total_texts_scanned += 1
                            
                            found_terms = set()
                            for end_idx, found_term in automaton.iter(src):
                                found_terms.add(found_term)
                            
                            text_id = f"{xml_path}_{locstr_idx}"
                            for term in found_terms:
                                term_text_sets[term].add(text_id)
                                
                    except Exception as e:
                        print(f"   ❌ Error parsing {xml_path}: {e}")

                step3_time = time.time() - step3_start
                avg_speed = total_texts_scanned / step3_time if step3_time > 0 else 0
                print(f"   ✅ STEP 3 COMPLETE: Scanned {total_texts_scanned:,} texts in {step3_time:.2f}s ({avg_speed:.0f} texts/sec)")

                # STEP 4: Filter by minimum occurrence
                progress_var.set("Filtering by minimum occurrence...")
                parent.update_idletasks()
                print(f"\n📊 STEP 4: Filtering terms (minimum occurrence: {min_occurrence_var.get()})")
                
                final_glossary = []
                terms_meeting_threshold = 0
                
                source_translations = defaultdict(lambda: defaultdict(int))
                for kr, tr in candidate_terms:
                    source_translations[kr][tr] += 1
                
                for kr, translations in source_translations.items():
                    occurrence_count = len(term_text_sets.get(kr, set()))
                    
                    if occurrence_count >= min_occurrence_var.get():
                        terms_meeting_threshold += 1
                        most_frequent_tr = max(translations.items(), key=lambda x: x[1])[0]
                        final_glossary.append((kr, most_frequent_tr, occurrence_count))
                
                print(f"   ✓ {terms_meeting_threshold:,}/{len(source_translations):,} terms meet minimum occurrence threshold")

                # STEP 5: Sort results
                progress_var.set("Sorting results...")
                parent.update_idletasks()
                print(f"\n🔤 Sorting {len(final_glossary):,} terms by: {sort_method_var.get()}")
                
                if sort_method_var.get() == "alphabetical":
                    final_glossary.sort(key=lambda x: x[0])
                elif sort_method_var.get() == "length":
                    final_glossary.sort(key=lambda x: len(x[0]))
                elif sort_method_var.get() == "frequency":
                    final_glossary.sort(key=lambda x: x[2], reverse=True)

                # STEP 6: Save results
                progress_var.set("Saving glossary...")
                parent.update_idletasks()
                
                with open(out, 'w', encoding='utf-8') as f:
                    for kr, tr, count in final_glossary:
                        f.write(f"{kr}\t{tr}\t[{count}]\n")

                total_time = time.time() - start_time
                
                print("\n" + "="*60)
                print("🎉 EXTRACTION COMPLETE!")
                print("="*60)
                print(f"📊 Initial candidates: {len(candidate_terms):,}")
                print(f"📊 Final glossary terms: {len(final_glossary):,}")
                print(f"⏱️  Total time: {total_time:.2f}s")
                print(f"⚡ Aho-Corasick scan speed: {avg_speed:.0f} texts/second")
                print("="*60)

                progress_var.set(f"Glossary extracted: {len(final_glossary)} terms (in {total_time:.1f}s)")
                messagebox.showinfo("Done", 
                    f"Glossary saved to:\n{out}\n\n"
                    f"Extracted {len(final_glossary)} terms from {total_texts_scanned:,} texts\n"
                    f"Aho-Corasick processing speed: {avg_speed:.0f} texts/sec!")

            except Exception:
                txt = traceback.format_exc()
                progress_var.set("Error during glossary extraction.")

                print("ERROR:", e)
                traceback.print_exc()

        threading.Thread(target=task, daemon=True).start()

    # --- LINE CHECK WITH NEW SUB-GUI ---
    def line_check_thread():
        # Create configuration dialog
        dialog = tk.Toplevel(parent)
        dialog.title("Line Check Configuration")
        dialog.geometry("450x400")
        dialog.transient(parent)
        dialog.grab_set()
        center_dialog(dialog, window)
        
        # Store selected files/folders
        source_data = {'files': None, 'folder': None, 'type': None}
        glossary_data = {'files': None, 'folder': None, 'type': None}
        
        # Mode selection
        mode_frame = ttk.LabelFrame(dialog, text="Check Mode")
        mode_frame.pack(padx=10, pady=5, fill="x")
        
        mode_var = tk.StringVar(value="self")
        ttk.Radiobutton(mode_frame, text="Source against Self", variable=mode_var, value="self").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Source against External Glossary", variable=mode_var, value="external").pack(anchor="w")
        
        # Source data frame
        source_frame = ttk.LabelFrame(dialog, text="Source Data")
        source_frame.pack(padx=10, pady=5, fill="x")
        
        source_file_btn = tk.Button(source_frame, text="Select Files", state=tk.NORMAL)
        source_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        source_folder_btn = tk.Button(source_frame, text="Select Folder", state=tk.NORMAL)
        source_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        source_label = tk.Label(source_frame, text="No data selected")
        source_label.pack(side=tk.LEFT, padx=10)
        
        # Glossary data frame (initially disabled)
        glossary_frame = ttk.LabelFrame(dialog, text="External Glossary Data")
        glossary_frame.pack(padx=10, pady=5, fill="x")
        
        glossary_file_btn = tk.Button(glossary_frame, text="Select Files", state=tk.DISABLED)
        glossary_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        glossary_folder_btn = tk.Button(glossary_frame, text="Select Folder", state=tk.DISABLED)
        glossary_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        glossary_label = tk.Label(glossary_frame, text="No data selected")
        glossary_label.pack(side=tk.LEFT, padx=10)
        
        def on_mode_change(*args):
            if mode_var.get() == "external":
                glossary_file_btn.config(state=tk.NORMAL)
                glossary_folder_btn.config(state=tk.NORMAL)
            else:
                glossary_file_btn.config(state=tk.DISABLED)
                glossary_folder_btn.config(state=tk.DISABLED)
        
        mode_var.trace('w', on_mode_change)
        
        def select_source_files():
            files = filedialog.askopenfilenames(
                title="Select Source XML/TXT Files",
                filetypes=[("XML and TXT Files", "*.xml *.txt *.tsv"), ("All Files", "*.*")]
            )
            if files:
                source_data['files'] = files
                source_data['folder'] = None
                source_data['type'] = 'files'
                source_label.config(text=f"{len(files)} files selected")
                source_folder_btn.config(state=tk.DISABLED)
        
        def select_source_folder():
            folder = filedialog.askdirectory(title="Select Source Folder")
            if folder:
                source_data['folder'] = folder
                source_data['files'] = None
                source_data['type'] = 'folder'
                source_label.config(text=f"Folder: {os.path.basename(folder)}")
                source_file_btn.config(state=tk.DISABLED)
        
        def select_glossary_files():
            files = filedialog.askopenfilenames(
                title="Select Glossary XML/TXT Files",
                filetypes=[("XML and TXT Files", "*.xml *.txt *.tsv"), ("All Files", "*.*")]
            )
            if files:
                glossary_data['files'] = files
                glossary_data['folder'] = None
                glossary_data['type'] = 'files'
                glossary_label.config(text=f"{len(files)} files selected")
                glossary_folder_btn.config(state=tk.DISABLED)
        
        def select_glossary_folder():
            folder = filedialog.askdirectory(title="Select Glossary Folder")
            if folder:
                glossary_data['folder'] = folder
                glossary_data['files'] = None
                glossary_data['type'] = 'folder'
                glossary_label.config(text=f"Folder: {os.path.basename(folder)}")
                glossary_file_btn.config(state=tk.DISABLED)
        
        source_file_btn.config(command=select_source_files)
        source_folder_btn.config(command=select_source_folder)
        glossary_file_btn.config(command=select_glossary_files)
        glossary_folder_btn.config(command=select_glossary_folder)
        
        def start_check():
            import string
            if not source_data['type']:
                messagebox.showwarning("Warning", "Please select source data")
                return
            
            if mode_var.get() == "external" and not glossary_data['type']:
                messagebox.showwarning("Warning", "Please select glossary data")
                return
            
            dialog.destroy()
            
            out = filedialog.asksaveasfilename(
                title="Save Line Report As",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")]
            )
            if not out:
                return
            
            def task():
                try:
                    progress_var.set("Checking line consistency...")
                    parent.update_idletasks()
                    
                    # Determine glossary source
                    if mode_var.get() == "self":
                        glossary_pairs = []
                        if source_data['type'] == 'files':
                            glossary_pairs = extract_all_pairs_from_files(source_data['files'], progress_var, parent)
                        else:
                            glossary_pairs = extract_all_pairs_from_folder(source_data['folder'], progress_var, parent)
                    else:
                        glossary_pairs = []
                        if glossary_data['type'] == 'files':
                            glossary_pairs = extract_all_pairs_from_files(glossary_data['files'], progress_var, parent)
                        else:
                            glossary_pairs = extract_all_pairs_from_folder(glossary_data['folder'], progress_var, parent)
                    
                    # ✅ IGNORE if Str contains Korean
                    glossary_pairs = [(kr, tr) for kr, tr in glossary_pairs if not is_korean(tr)]
                    
                    # ✅ Apply glossary extraction filters
                    glossary_pairs = glossary_filter(
                        glossary_pairs,
                        glossary_length_var.get(),
                        filter_sentences_var.get(),
                        min_occurrence_var.get()
                    )
                    
                    glossary_grouping = defaultdict(set)
                    for kr, tr in glossary_pairs:
                        glossary_grouping[kr].add(tr)
                    
                    # Get check files
                    check_files = []
                    if source_data['type'] == 'files':
                        check_files = source_data['files']
                    else:
                        for root, dirs, files in os.walk(source_data['folder']):
                            for file in files:
                                if file.lower().endswith((".xml", ".txt", ".tsv")):
                                    check_files.append(os.path.join(root, file))
                    
                    # Build mapping
                    src_tr_file = defaultdict(lambda: defaultdict(set))
                    for idx, file_path in enumerate(check_files, 1):
                        progress_var.set(f"Parsing {idx}/{len(check_files)}: {os.path.basename(file_path)}")
                        parent.update_idletasks()
                        ext = os.path.splitext(file_path)[1].lower()
                        try:
                            if ext == ".xml":
                                parser = etree.XMLParser(recover=True, resolve_entities=False)
                                tree = etree.parse(file_path, parser)
                                for locstr in tree.xpath('//LocStr'):
                                    src = locstr.get('StrOrigin', '').strip()
                                    tgt = locstr.get('Str', '').strip()
                                    if src and tgt and not is_korean(tgt):
                                        # ✅ Apply sentence filter
                                        if filter_sentences_var.get() and re.search(r'[.?!]\s*$', src.strip()):
                                            continue
                                        # ✅ Skip if contains punctuation or special ellipsis
                                        if any(ch in string.punctuation for ch in src) or '…' in src:
                                            continue
                                        src_tr_file[src][tgt].add(os.path.basename(file_path))
                            elif ext in (".txt", ".tsv"):
                                df = pd.read_csv(
                                    file_path,
                                    delimiter="\t",
                                    header=None,
                                    dtype=str,
                                    quoting=csv.QUOTE_NONE,
                                    quotechar=None,
                                    escapechar=None,
                                    na_values=[''],
                                    keep_default_na=False
                                )
                                if len(df.columns) >= 7:
                                    for _, row in df.iterrows():
                                        src = str(row[5]).strip() if pd.notna(row[5]) else ""
                                        tgt = str(row[6]).strip() if pd.notna(row[6]) else ""
                                        if src and tgt and not is_korean(tgt):
                                            if filter_sentences_var.get() and re.search(r'[.?!]\s*$', src.strip()):
                                                continue
                                            if any(ch in string.punctuation for ch in src) or '…' in src:
                                                continue
                                            src_tr_file[src][tgt].add(os.path.basename(file_path))
                        except Exception as e:
                            print(f"Failed {file_path}: {e}")
                    
                    inconsistent = {src: tr_dict for src, tr_dict in src_tr_file.items() if len(tr_dict) > 1}
                    
                    with open(out, 'w', encoding='utf-8') as f:
                        for src, tr_dict in sorted(inconsistent.items(), key=lambda x: len(x[0])):
                            f.write(f"{src}\n")
                            for tr, files in sorted(tr_dict.items()):
                                for file in sorted(files):
                                    f.write(f"  {tr}    [{file}]\n")
                            f.write("\n")
                    
                    progress_var.set(f"Line check complete: {len(inconsistent)} sources inconsistent")
                    messagebox.showinfo("Done", f"Line report saved to:\n{out}")
                    
                except Exception:
                    traceback.print_exc()
                    progress_var.set("Error during line check.")
            
            threading.Thread(target=task, daemon=True).start()
        
        start_btn = tk.Button(dialog, text="Start Check", command=start_check,
                             relief="raised", bd=3, padx=20, pady=5,
                             font=('Helvetica', 10, 'bold'))
        start_btn.pack(pady=10)

    # --- TERM CHECK WITH NEW SUB-GUI ---
    def term_check_thread():
        # Create configuration dialog
        dialog = tk.Toplevel(parent)
        dialog.title("Term Check Configuration")
        dialog.geometry("450x400")
        dialog.transient(parent)
        dialog.grab_set()
        center_dialog(dialog, window)
        
        # Store selected files/folders
        source_data = {'files': None, 'folder': None, 'type': None}
        glossary_data = {'files': None, 'folder': None, 'type': None}
        
        # Mode selection
        mode_frame = ttk.LabelFrame(dialog, text="Check Mode")
        mode_frame.pack(padx=10, pady=5, fill="x")
        
        mode_var = tk.StringVar(value="self")
        ttk.Radiobutton(mode_frame, text="Source against Self", variable=mode_var, value="self").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Source against External Glossary", variable=mode_var, value="external").pack(anchor="w")
        
        # Source data frame
        source_frame = ttk.LabelFrame(dialog, text="Source Data")
        source_frame.pack(padx=10, pady=5, fill="x")
        
        source_file_btn = tk.Button(source_frame, text="Select Files", state=tk.NORMAL)
        source_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        source_folder_btn = tk.Button(source_frame, text="Select Folder", state=tk.NORMAL)
        source_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        source_label = tk.Label(source_frame, text="No data selected")
        source_label.pack(side=tk.LEFT, padx=10)
        
        # Glossary data frame (initially disabled)
        glossary_frame = ttk.LabelFrame(dialog, text="External Glossary Data")
        glossary_frame.pack(padx=10, pady=5, fill="x")
        
        glossary_file_btn = tk.Button(glossary_frame, text="Select Files", state=tk.DISABLED)
        glossary_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        glossary_folder_btn = tk.Button(glossary_frame, text="Select Folder", state=tk.DISABLED)
        glossary_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        glossary_label = tk.Label(glossary_frame, text="No data selected")
        glossary_label.pack(side=tk.LEFT, padx=10)
        
        def on_mode_change(*args):
            if mode_var.get() == "external":
                glossary_file_btn.config(state=tk.NORMAL)
                glossary_folder_btn.config(state=tk.NORMAL)
            else:
                glossary_file_btn.config(state=tk.DISABLED)
                glossary_folder_btn.config(state=tk.DISABLED)
        
        mode_var.trace('w', on_mode_change)
        
        def select_source_files():
            files = filedialog.askopenfilenames(
                title="Select Source XML/TXT Files",
                filetypes=[
                    ("XML and TXT Files", "*.xml *.txt *.tsv"),
                    ("XML Files", "*.xml"),
                    ("Text Files", "*.txt;*.tsv"),
                    ("All Files", "*.*")
                ]
            )
            if files:
                source_data['files'] = files
                source_data['folder'] = None
                source_data['type'] = 'files'
                source_label.config(text=f"{len(files)} files selected")
                source_folder_btn.config(state=tk.DISABLED)
        
        def select_source_folder():
            folder = filedialog.askdirectory(title="Select Source Folder")
            if folder:
                source_data['folder'] = folder
                source_data['files'] = None
                source_data['type'] = 'folder'
                source_label.config(text=f"Folder: {os.path.basename(folder)}")
                source_file_btn.config(state=tk.DISABLED)
        
        def select_glossary_files():
            files = filedialog.askopenfilenames(
                title="Select Glossary XML/TXT Files",
                filetypes=[
                    ("XML and TXT Files", "*.xml *.txt *.tsv"),
                    ("XML Files", "*.xml"),
                    ("Text Files", "*.txt;*.tsv"),
                    ("All Files", "*.*")
                ]
            )
            if files:
                glossary_data['files'] = files
                glossary_data['folder'] = None
                glossary_data['type'] = 'files'
                glossary_label.config(text=f"{len(files)} files selected")
                glossary_folder_btn.config(state=tk.DISABLED)
        
        def select_glossary_folder():
            folder = filedialog.askdirectory(title="Select Glossary Folder")
            if folder:
                glossary_data['folder'] = folder
                glossary_data['files'] = None
                glossary_data['type'] = 'folder'
                glossary_label.config(text=f"Folder: {os.path.basename(folder)}")
                glossary_file_btn.config(state=tk.DISABLED)
        
        source_file_btn.config(command=select_source_files)
        source_folder_btn.config(command=select_source_folder)
        glossary_file_btn.config(command=select_glossary_files)
        glossary_folder_btn.config(command=select_glossary_folder)
        
        def start_check():
            if not source_data['type']:
                messagebox.showwarning("Warning", "Please select source data")
                return
            
            if mode_var.get() == "external" and not glossary_data['type']:
                messagebox.showwarning("Warning", "Please select glossary data")
                return
            
            dialog.destroy()
            
            def task():
                try:
                    import time
                    start_time = time.time()
                    
                    progress_var.set("Extracting working glossary...")
                    parent.update_idletasks()
                    
                    # Determine glossary source
                    if mode_var.get() == "self":
                        glossary_pairs = []
                        if source_data['type'] == 'files':
                            glossary_pairs = extract_all_pairs_from_files(source_data['files'], progress_var, parent)
                        else:
                            glossary_pairs = extract_all_pairs_from_folder(source_data['folder'], progress_var, parent)
                    else:
                        glossary_pairs = []
                        if glossary_data['type'] == 'files':
                            glossary_pairs = extract_all_pairs_from_files(glossary_data['files'], progress_var, parent)
                        else:
                            glossary_pairs = extract_all_pairs_from_folder(glossary_data['folder'], progress_var, parent)
                    
                    glossary_pairs = [(kr, tr) for kr, tr in glossary_pairs if not is_korean(tr)]
                    glossary_pairs = glossary_filter(
                        glossary_pairs,
                        glossary_length_var.get(),
                        filter_sentences_var.get(),
                        min_occurrence_var.get()
                    )
                    
                    seen = set()
                    glossary_terms = []
                    for kr, tr in glossary_pairs:
                        if kr not in seen:
                            glossary_terms.append((kr, tr))
                            seen.add(kr)
                    
                    if not glossary_terms:
                        progress_var.set("No glossary terms found.")
                        messagebox.showwarning("No entries", "No glossary terms could be extracted.")
                        return
                    
                    progress_var.set(f"Glossary extracted: {len(glossary_terms)} terms. Building Aho-Corasick automaton...")
                    parent.update_idletasks()
                    
                    import ahocorasick
                    automaton = ahocorasick.Automaton()
                    term_to_translation = {}
                    
                    for kr_term, ref_tr in glossary_terms:
                        automaton.add_word(kr_term, (len(term_to_translation), kr_term))
                        term_to_translation[len(term_to_translation)] = (kr_term, ref_tr)
                    
                    automaton.make_automaton()
                    
                    def is_isolated(text, start, end):
                        before = text[start - 1] if start > 0 else ""
                        after = text[end] if end < len(text) else ""
                        return (not re.match(r'[\w가-힣]', before)) and (not re.match(r'[\w가-힣]', after))
                    
                    progress_var.set("Starting Aho-Corasick scan with isolation check...")
                    parent.update_idletasks()
                    
                    issues = defaultdict(list)
                    check_files = []
                    if source_data['type'] == 'files':
                        check_files = source_data['files']
                    else:
                        for root, dirs, files in os.walk(source_data['folder']):
                            for file in files:
                                if file.endswith('.xml'):
                                    check_files.append(os.path.join(root, file))
                    
                    for idx, xml_path in enumerate(check_files, 1):
                        if idx % 10 == 0:
                            progress = (idx / len(check_files)) * 100
                            progress_var.set(f"Aho-Corasick scan: {progress:.1f}%")
                            parent.update_idletasks()
                        
                        try:
                            parser = etree.XMLParser(recover=True, resolve_entities=False)
                            tree = etree.parse(xml_path, parser)
                            
                            for locstr in tree.xpath('//LocStr'):
                                src = locstr.get('StrOrigin', '').strip()
                                tgt = locstr.get('Str', '').strip()
                                if not src or not tgt or is_korean(tgt):
                                    continue
                                if filter_sentences_var.get() and re.search(r'[.?!]\s*$', src.strip()):
                                    continue
                                
                                matches_found = set()
                                for end_index, (pattern_id, original_term) in automaton.iter(src):
                                    start_index = end_index - len(original_term) + 1
                                    if is_isolated(src, start_index, end_index + 1):
                                        matches_found.add(pattern_id)
                                
                                for pattern_id in matches_found:
                                    kr_term, ref_tr = term_to_translation[pattern_id]
                                    # ✅ Case-insensitive containment check
                                    if ref_tr.lower() not in tgt.lower():
                                        issues[(kr_term, ref_tr)].append((src, tgt, os.path.basename(xml_path)))
                        
                        except Exception as e:
                            print(f"Failed {xml_path}: {e}")
                    
                    # HARD FILTER: Remove terms with more than 6 flags
                    issues = {k: v for k, v in issues.items() if len(v) <= 6}
                    
                    out_dir = os.path.join(get_base_dir(), "Glossary_Term_Check")
                    os.makedirs(out_dir, exist_ok=True)
                    dt_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_file = os.path.join(out_dir, f"TermCheck_{dt_str}.txt")
                    
                    with open(out_file, 'w', encoding='utf-8') as f:
                        for (kr_term, ref_tr), problem_lines in sorted(issues.items(), key=lambda x: len(x[0][0])):
                            f.write(f"{kr_term} // {ref_tr}\n")
                            for src, tgt, rel in problem_lines:
                                f.write(f"{rel} | Source: \"{src}\" | Trans: \"{tgt}\"\n")
                            f.write("\n")
                    
                    total_time = time.time() - start_time
                    progress_var.set(f"Term check complete: {len(issues)} terms with issues (in {total_time:.1f}s)")
                    messagebox.showinfo("Done", f"Term report saved to:\n{out_file}")
                
                except Exception:
                    traceback.print_exc()
                    progress_var.set("Error during term check.")
            
            threading.Thread(target=task, daemon=True).start()
        
        start_btn = tk.Button(dialog, text="Start Check", command=start_check,
                             relief="raised", bd=3, padx=20, pady=5,
                             font=('Helvetica', 10, 'bold'))
        start_btn.pack(pady=10)

    # --- NEW: Pattern Sequence Check for XML LocStr ---
    def pattern_sequence_check_thread():
        xml_files = filedialog.askopenfilenames(
            title="Select Source XML/TXT Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("XML Files", "*.xml"),
                ("Text Files", "*.txt;*.tsv"),
                ("All Files", "*.*")
            ]
        )
        if not xml_files:
            return

        out = filedialog.asksaveasfilename(
            title="Save Pattern Sequence Check Report As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not out:
            return

        def extract_code_patterns(text):
            # Extract {...} patterns, non-greedy
            return set(re.findall(r'\{.*?\}', text))

        def task():
            try:
                progress_var.set("Checking pattern sequences...")
                parent.update_idletasks()

                all_entries = extract_all_locstrs_from_files(xml_files, progress_var, parent)
                mismatches = []

                for entry in all_entries:
                    col5 = entry['StrOrigin']
                    col6 = entry['Str']
                    patterns_5 = extract_code_patterns(col5)
                    patterns_6 = extract_code_patterns(col6)
                    if patterns_5 != patterns_6:
                        mismatches.append(
                            f"{os.path.basename(entry['xml_path'])} | StrOrigin: \"{col5}\" | Str: \"{col6}\"\n"
                        )

                with open(out, 'w', encoding='utf-8') as f:
                    for line in mismatches:
                        f.write(line)

                progress_var.set(f"Pattern sequence check complete: {len(mismatches)} mismatches found")
                messagebox.showinfo("Done", f"Pattern sequence check report saved to:\n{out}")

            except Exception:
                txt = traceback.format_exc()
                progress_var.set("Error during pattern sequence check.")

                print("ERROR:", e)
                traceback.print_exc()

        threading.Thread(target=task, daemon=True).start()

    # --- NEW: Character Count Check for XML LocStr ---
    def character_count_check_thread():
        # Sub-GUI for selecting symbol set
        def get_symbol_set():
            dialog = tk.Toplevel(parent)
            dialog.title("특수 문자 체크 옵션 선택")
            dialog.geometry("350x200")

            var_option = tk.StringVar(value="BDO")  # Default selection is BDO
            symbols_result = {}

            tk.Label(dialog, text="어떤 심볼을 체크할까요?").pack(padx=10, pady=10)

            rb_bdo = tk.Radiobutton(dialog, text="BDO 특수 문자 체크 ({, })", variable=var_option, value="BDO")
            rb_bdo.pack(anchor="w", padx=20)
            rb_bdm = tk.Radiobutton(dialog, text="BDM 특수 문자 체크 (▶, {, }, 🔗, |)", variable=var_option, value="BDM")
            rb_bdm.pack(anchor="w", padx=20)
            rb_custom = tk.Radiobutton(dialog, text="사용자 지정 문자", variable=var_option, value="CUSTOM")
            rb_custom.pack(anchor="w", padx=20)

            custom_entry = tk.Entry(dialog, state="disabled")
            custom_entry.pack(padx=20, pady=5, fill="x")

            def on_option_change(*args):
                if var_option.get() == "CUSTOM":
                    custom_entry.config(state="normal")
                else:
                    custom_entry.delete(0, tk.END)
                    custom_entry.config(state="disabled")
            var_option.trace("w", on_option_change)

            def on_ok():
                option = var_option.get()
                if option == "BDO":
                    symbols_result['symbols'] = ["{", "}"]
                elif option == "BDM":
                    symbols_result['symbols'] = ["▶", "{", "}", "🔗", "|"]
                elif option == "CUSTOM":
                    custom_value = custom_entry.get().strip()
                    if not custom_value:
                        messagebox.showerror("Error", "사용자 지정 심볼을 입력해 주세요.")                       
                        return
                    symbols_result['symbols'] = list(custom_value)
                dialog.destroy()

            ok_button = tk.Button(dialog, text="확인", command=on_ok)
            ok_button.pack(pady=10)

            dialog.grab_set()
            dialog.wait_window()
            return symbols_result.get('symbols')

        symbols = get_symbol_set()
        if not symbols:
            return  # User cancelled or did not complete selection

        xml_files = filedialog.askopenfilenames(
            title="Select Source XML/TXT Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("XML Files", "*.xml"),
                ("Text Files", "*.txt;*.tsv"),
                ("All Files", "*.*")
            ]
        )
        if not xml_files:
            return

        out = filedialog.asksaveasfilename(
            title="Save Character Count Check Report As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not out:
            return

        def preprocess_text(text):
            # Remove formatting codes that may interfere
            text = re.sub(r'<color:.*?>', '', text)
            text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
            return text

        def task():
            try:
                progress_var.set("Checking character counts...")
                parent.update_idletasks()

                all_entries = extract_all_locstrs_from_files(xml_files, progress_var, parent)
                mismatches = []

                for entry in all_entries:
                    col5 = preprocess_text(entry['StrOrigin'])
                    col6 = preprocess_text(entry['Str'])
                    for sym in symbols:
                        if col5.count(sym) != col6.count(sym):
                            mismatches.append(
                                f"{os.path.basename(entry['xml_path'])} | StrOrigin: \"{entry['StrOrigin']}\" | Str: \"{entry['Str']}\"\n"
                            )
                            break  # Only add once per entry

                with open(out, 'w', encoding='utf-8') as f:
                    for line in mismatches:
                        f.write(line)

                progress_var.set(f"Character count check complete: {len(mismatches)} mismatches found")
                messagebox.showinfo("Done", f"Character count check report saved to:\n{out}")

            except Exception:
                txt = traceback.format_exc()
                progress_var.set("Error during character count check.")
                print("ERROR:", e)
                traceback.print_exc()

        threading.Thread(target=task, daemon=True).start()

    # --- Build UI ---
    frame = tk.Frame(parent)
    frame.pack(pady=10)

    # --- Options Frame ---
    options_frame = tk.LabelFrame(frame, text="Glossary Extraction Options")
    options_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

    # Sentence filter checkbox
    sentence_cb = tk.Checkbutton(
        options_frame,
        text="Filter out sentences (end with . ? !)",
        variable=filter_sentences_var
    )
    sentence_cb.pack(anchor='w', padx=5, pady=2)

    # Glossary length threshold spinbox
    threshold_label = tk.Label(options_frame, text="Max source length:")
    threshold_label.pack(anchor='w', padx=5, pady=(8, 0))
    threshold_spin = tk.Spinbox(
        options_frame,
        from_=3, to=50,
        textvariable=glossary_length_var,
        width=5
    )
    threshold_spin.pack(anchor='w', padx=5, pady=2)

    # Minimum occurrence setting
    occurrence_frame = tk.Frame(options_frame)
    occurrence_frame.pack(fill=tk.X, pady=5)
    tk.Label(occurrence_frame, text="Minimum occurrence count:").pack(side=tk.LEFT)
    occurrence_spinbox = tk.Spinbox(occurrence_frame, from_=1, to=50, textvariable=min_occurrence_var, width=10)
    occurrence_spinbox.pack(side=tk.RIGHT)

    # Sorting options
    sort_frame = tk.LabelFrame(options_frame, text="Output Sorting")
    sort_frame.pack(fill=tk.X, pady=10)

    tk.Radiobutton(sort_frame, text="Alphabetical order", 
                   variable=sort_method_var, value="alphabetical").pack(anchor='w')
    tk.Radiobutton(sort_frame, text="Length order (shortest to longest)", 
                   variable=sort_method_var, value="length").pack(anchor='w')
    tk.Radiobutton(sort_frame, text="Frequency order (most to least common)", 
                   variable=sort_method_var, value="frequency").pack(anchor='w')

    # --- Buttons Frame ---
    buttons_frame = tk.Frame(frame)
    buttons_frame.pack(side=tk.LEFT, padx=10, pady=5)

    btn1 = tk.Button(buttons_frame,
                     text="Extract Glossary",
                     font='Helvetica 10 bold',
                     command=extract_glossary_thread)
    btn1.pack(fill=tk.X, pady=2)

    btn2 = tk.Button(buttons_frame,
                     text="Line Check",
                     font='Helvetica 10 bold',
                     command=line_check_thread)
    btn2.pack(fill=tk.X, pady=2)

    btn3 = tk.Button(buttons_frame,
                     text="Term Check",
                     font='Helvetica 10 bold',
                     command=term_check_thread)
    btn3.pack(fill=tk.X, pady=2)

    # --- NEW BUTTONS ---
    btn4 = tk.Button(buttons_frame,
                     text="패턴 시퀸스 체크",
                     font='Helvetica 10 bold',
                     command=pattern_sequence_check_thread)
    btn4.pack(fill=tk.X, pady=2)

    btn5 = tk.Button(buttons_frame,
                     text="문자 개수 체크",
                     font='Helvetica 10 bold',
                     command=character_count_check_thread)
    btn5.pack(fill=tk.X, pady=2)

    # --- Status ---
    status = tk.Label(parent, textvariable=progress_var, anchor='w')
    status.pack(fill=tk.X, padx=10, pady=5)

# Create main window
window = tk.Tk()
window.title("Quick Search XML - Version: 0818 (By Neil)")
window.geometry("800x800")

# Try to set icon - handle case where it might not exist
try:
    icon_path = os.path.join(get_base_dir(), "images", "QSico.ico")
    if os.path.exists(icon_path):
        window.iconbitmap(icon_path)
    else:
        # Try without images folder
        icon_path = os.path.join(get_base_dir(), "QSico.ico")
        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
except:
    pass  # Icon not found, continue without it

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
show_string_key = True 
string_keys = {}
stringid_to_entry = {}

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