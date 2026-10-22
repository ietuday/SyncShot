package main

import "fmt"

func calculateHike(salary, percentage float64) float64 {
	return salary * percentage / 100
}

func calculateNewSalary(salary, hike float64) float64 {
	return salary + hike
}

func calculateMonthlySalary(annualSalary float64) float64 {
	return annualSalary / 12
}

func main() {
	salary := 600000.0
	percentage := 10.0

	hike := calculateHike(salary, percentage)
	newSalary := calculateNewSalary(salary, hike)
	monthlySalary := calculateMonthlySalary(newSalary)

	fmt.Println("Hike:", hike)
	fmt.Println("New Annual Salary:", newSalary)
	fmt.Println("Monthly Salary:", monthlySalary)
}
