package utils

import "context"

type renderProgressKey struct{}

// WithRenderProgress reports progress as a fraction of the render work.
func WithRenderProgress(ctx context.Context, report func(float64)) context.Context {
	return context.WithValue(ctx, renderProgressKey{}, report)
}

// RenderProgressRange maps a render pass into its share of the overall work.
func RenderProgressRange(ctx context.Context, start, end float64) context.Context {
	if report, ok := ctx.Value(renderProgressKey{}).(func(float64)); ok {
		return WithRenderProgress(ctx, func(fraction float64) {
			report(start + (end-start)*fraction)
		})
	}
	return ctx
}

func ReportRenderProgress(ctx context.Context, fraction float64) {
	if report, ok := ctx.Value(renderProgressKey{}).(func(float64)); ok {
		report(min(1, max(0, fraction)))
	}
}

type renderProgressDurationKey struct{}

// WithRenderProgressDuration sets the precise duration of one FFmpeg pass.
func WithRenderProgressDuration(ctx context.Context, duration float64) context.Context {
	return context.WithValue(ctx, renderProgressDurationKey{}, duration)
}

func HasRenderProgress(ctx context.Context) bool {
	_, ok := ctx.Value(renderProgressKey{}).(func(float64))
	return ok
}
