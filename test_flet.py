import flet as ft
def main(page: ft.Page):
    try:
        s = ft.TextStyle(letter_spacing=1.2)
        print(f"Success: TextStyle(letter_spacing=1.2)")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error: {e}")
        print(f"Error: {e}")
        print(f"Error: {e}")
ft.app(target=main)
