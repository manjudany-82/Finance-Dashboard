"""
Premium Chart Styling Configuration
Centralized chart styling for consistent premium look across all visualizations
"""

# Color Palette
COLORS = {
    'primary': '#6366F1',      # Indigo
    'secondary': '#8B5CF6',    # Purple
    'success': '#10B981',      # Green
    'warning': '#F59E0B',      # Amber
    'danger': '#EF4444',       # Red
    'info': '#3B82F6',         # Blue
    'blue_light': '#60A5FA',   # Light Blue
    'green_light': '#34D399',  # Light Green
    'purple_light': '#A78BFA', # Light Purple
    'yellow': '#FCD34D',       # Yellow
}

# Chart Template
CHART_TEMPLATE = {
    'layout': {
        'plot_bgcolor': 'rgba(255, 255, 255, 0.02)',
        'paper_bgcolor': 'rgba(255, 255, 255, 0.02)',
        'font': {
            'family': 'Inter, sans-serif',
            'color': '#F9FAFB',
            'size': 12
        },
        'title': {
            'font': {
                'size': 16,
                'color': '#F9FAFB',
                'family': 'Inter, sans-serif'
            },
            'x': 0.02,
            'xanchor': 'left'
        },
        'xaxis': {
            'gridcolor': 'rgba(255, 255, 255, 0.08)',
            'gridwidth': 1,
            'showgrid': True,
            'zeroline': False,
            'color': '#9CA3AF',
            'tickfont': {'size': 11}
        },
        'yaxis': {
            'gridcolor': 'rgba(255, 255, 255, 0.08)',
            'gridwidth': 1,
            'showgrid': True,
            'zeroline': False,
            'color': '#9CA3AF',
            'tickfont': {'size': 11}
        },
        'legend': {
            'bgcolor': 'rgba(255, 255, 255, 0.05)',
            'bordercolor': 'rgba(255, 255, 255, 0.1)',
            'borderwidth': 1,
            'font': {'size': 11, 'color': '#F9FAFB'},
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': 'rgba(10, 14, 39, 0.95)',
            'bordercolor': 'rgba(99, 102, 241, 0.5)',
            'font': {'size': 12, 'color': '#F9FAFB'}
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
    }
}

def get_bar_config(color=COLORS['primary'], opacity=0.8):
    """Get configuration for bar charts"""
    return {
        'marker': {
            'color': color,
            'opacity': opacity,
            'line': {'width': 0}
        }
    }

def get_line_config(color=COLORS['warning'], width=3, dash=None):
    """Get configuration for line charts"""
    config = {
        'line': {
            'color': color,
            'width': width,
            'shape': 'spline',  # Smooth curves
        },
        'mode': 'lines+markers',
        'marker': {
            'size': 6,
            'color': color,
            'line': {'width': 2, 'color': 'rgba(10, 14, 39, 0.8)'}
        }
    }
    if dash:
        config['line']['dash'] = dash
    return config

def get_area_config(color=COLORS['success'], opacity=0.3):
    """Get configuration for area charts"""
    return {
        'fill': 'tonexty',
        'fillcolor': f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {opacity})',
        'line': {'width': 2, 'color': color, 'shape': 'spline'}
    }

def apply_chart_style(fig):
    """Apply premium styling to a Plotly figure"""
    fig.update_layout(CHART_TEMPLATE['layout'])
    return fig

def create_combo_chart_layout():
    """Create layout for combo charts (bars + line)"""
    layout = CHART_TEMPLATE['layout'].copy()
    layout.update({
        'barmode': 'stack',
        'yaxis2': {
            'gridcolor': 'rgba(255, 255, 255, 0)',  # Hide secondary grid
            'showgrid': False,
            'zeroline': False,
            'color': '#9CA3AF',
            'overlaying': 'y',
            'side': 'right',
            'tickfont': {'size': 11}
        }
    })
    return layout
